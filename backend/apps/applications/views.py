from pathlib import Path

from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.response import Response

from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from api.core import events
from apps.opportunities.eligibility import evaluate_eligibility
from apps.opportunities.models import Opportunity
from apps.students.models import StudentProfile
from apps.students.permissions import IsStudent

from .models import Application, ApplicationStatusHistory
from .serializers import ApplicationSerializer, ApplicationSubmissionSerializer


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
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
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
                events.emit(
                    "application.submitted",
                    {"application_id": application.pk},
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
