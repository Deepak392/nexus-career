from pathlib import Path

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.opportunities.eligibility import evaluate_eligibility
from apps.opportunities.models import Opportunity
from apps.students.models import StudentProfile
from apps.students.permissions import IsStudent

from .models import Application, ApplicationStatusHistory
from .serializers import (
    ApplicationSerializer,
    ApplicationStatusUpdateSerializer,
    ApplicationSubmissionSerializer,
)


class ApplicationConflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "You have already applied for this opportunity."
    default_code = "duplicate_application"


class ApplicationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [permissions.IsAuthenticated, IsStudent]
    serializer_class = ApplicationSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("status", "transition"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsStudent()]

    def get_queryset(self):
        if self.action in ("status", "transition"):
            return (
                Application.objects.all()
                .select_related("opportunity", "opportunity__company", "student")
                .prefetch_related("status_history", "status_history__changed_by")
            )
        return (
            Application.objects.filter(student=self.request.user)
            .select_related("opportunity", "opportunity__company")
            .prefetch_related("status_history", "status_history__changed_by")
        )

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        submission = ApplicationSubmissionSerializer(data=request.data)
        submission.is_valid(raise_exception=True)
        opportunity_id = submission.validated_data["opportunity_id"]

        opportunity = get_object_or_404(
            Opportunity.objects.select_for_update().select_related("company"),
            pk=opportunity_id,
        )
        if opportunity.status != Opportunity.Status.PUBLISHED:
            raise ValidationError(
                {"opportunity": "This opportunity is not open for applications."}
            )
        if opportunity.application_deadline <= timezone.now():
            raise ValidationError(
                {"opportunity": "The application deadline has passed."}
            )
        if opportunity.application_method == "EXTERNAL":
            raise ValidationError(
                {
                    "opportunity": (
                        "This opportunity uses an external application link. "
                        "Apply on the company website."
                    )
                }
            )

        profile = StudentProfile.objects.filter(user=request.user).first()
        if profile is None:
            raise ValidationError(
                {"profile": "Create your student profile before applying."}
            )

        eligibility = evaluate_eligibility(opportunity, profile)
        if eligibility["eligible"] is not True:
            raise ValidationError({"eligibility": eligibility})

        if not profile.has_resume:
            raise ValidationError(
                {
                    "resume": (
                        "Upload a valid PDF resume in your student profile "
                        "before applying."
                    )
                }
            )

        if Application.objects.filter(
            student=request.user,
            opportunity=opportunity,
        ).exists():
            raise ApplicationConflict()

        application = Application(
            student=request.user,
            opportunity=opportunity,
            eligibility_snapshot=eligibility,
        )
        saved_file = None
        try:
            # Store the exact resume bytes used at submission time. The FileField
            # upload_to function assigns a fresh generated private filename.
            with profile.resume.open("rb") as resume_source:
                resume_content = resume_source.read()
            application.resume.save(
                "resume.pdf",
                ContentFile(resume_content),
                save=False,
            )
            saved_file = application.resume
            with transaction.atomic():
                application.save(force_insert=True)
                ApplicationStatusHistory.objects.create(
                    application=application,
                    status=Application.Status.SUBMITTED,
                    changed_by=request.user,
                    note="Application submitted by student.",
                )
                Notification.objects.create(
                    recipient=request.user,
                    notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
                    title="Application submitted",
                    message=(
                        f"Your application for {opportunity.title} at "
                        f"{opportunity.company.name} was submitted successfully."
                    ),
                    application=application,
                )
        except IntegrityError as exc:
            if saved_file:
                saved_file.delete(save=False)
            raise ApplicationConflict() from exc
        except Exception:
            if saved_file:
                saved_file.delete(save=False)
            raise

        response = ApplicationSerializer(
            application,
            context=self.get_serializer_context(),
        )
        return Response(response.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Transition application status",
        description="Update application status through permitted lifecycle states. Enforces role-based permissions and emits status change notifications.",
        request=ApplicationStatusUpdateSerializer,
        responses={200: ApplicationSerializer},
    )
    @action(detail=True, methods=["patch", "post"])
    def status(self, request, pk=None):
        """Update or transition application status (Recruiter, IPC Admin, or Student withdraw)."""
        application = get_object_or_404(
            Application.objects.select_related("opportunity", "opportunity__company", "student"),
            pk=pk,
        )

        user = request.user
        role = getattr(user, "role", "")
        is_ipc_admin = role in ("IPC_ADMIN", "SYSTEM_ADMIN") or user.is_staff or user.is_superuser
        is_recruiter = role == "RECRUITER"
        is_student = role == "STUDENT" and application.student_id == user.id

        if is_recruiter:
            profile = getattr(user, "recruiter_profile", None)
            if not profile or profile.company_id != application.opportunity.company_id:
                raise PermissionDenied("You can only update applications for your own company.")
        elif is_student:
            pass  # Allowed only for WITHDRAWN below
        elif not is_ipc_admin:
            raise PermissionDenied("You are not authorized to update this application.")

        update_serializer = ApplicationStatusUpdateSerializer(data=request.data)
        update_serializer.is_valid(raise_exception=True)
        new_status = update_serializer.validated_data["status"]
        note = update_serializer.validated_data.get("note", "")

        if is_student and new_status != Application.Status.WITHDRAWN:
            raise ValidationError({"status": "Students can only transition an application to WITHDRAWN."})

        try:
            from .services import transition_application_status

            application = transition_application_status(
                application=application,
                new_status=new_status,
                actor=user,
                note=note,
            )
        except DjangoValidationError as exc:
            msg = exc.messages if hasattr(exc, "messages") else str(exc)
            raise ValidationError({"status": msg})

        return Response(
            ApplicationSerializer(application, context=self.get_serializer_context()).data,
            status=status.HTTP_200_OK,
        )
