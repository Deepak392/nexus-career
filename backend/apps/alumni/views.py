from api.core import audit
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema

from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.notifications.models import Notification

from .models import AlumniProfile, ReferralRequest, ReferralRequestHistory
from .serializers import (
    AlumniEngagementMetricsSerializer,
    AlumniProfileSerializer,
    AlumniSearchSerializer,
    AlumniVerificationActionSerializer,
    AlumniVerificationResponseSerializer,
    AlumniVerificationSerializer,
    GraduationProofUploadSerializer,
    ReferralRequestActionSerializer,
    ReferralRequestCreateSerializer,
    ReferralRequestSerializer,
)


class AlumniProfileView(
    generics.GenericAPIView,
):
    serializer_class = AlumniProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_alumni_role(self):
        if self.request.user.role != User.Role.ALUMNI:
            raise PermissionDenied("Only alumni can access alumni profiles.")

    def get_object(self):
        self.check_alumni_role()
        return get_object_or_404(AlumniProfile, user=self.request.user)

    def get(self, request, *args, **kwargs):
        return Response(self.get_serializer(self.get_object()).data)

    def post(self, request, *args, **kwargs):
        self.check_alumni_role()
        if AlumniProfile.objects.filter(user=request.user).exists():
            raise ValidationError({"detail": "You already have an alumni profile."})
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save(user=request.user)
        return Response(
            self.get_serializer(profile).data,
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def save_profile_update(profile, serializer):
        academic_fields = ("department", "degree_programme", "graduation_year")
        academic_details_changed = any(
            field in serializer.validated_data
            and serializer.validated_data[field] != getattr(profile, field)
            for field in academic_fields
        )
        profile = serializer.save()
        if academic_details_changed:
            profile.verification_status = AlumniProfile.VerificationStatus.PENDING
            profile.verification_rejection_reason = ""
            profile.verified_by = None
            profile.verified_at = None
            profile.reviewed_by = None
            profile.reviewed_at = None
            profile.save(
                update_fields=[
                    "verification_status",
                    "verification_rejection_reason",
                    "verified_by",
                    "verified_at",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )
        return profile

    def put(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.save_profile_update(profile, serializer)
        return Response(self.get_serializer(profile).data)

    def patch(self, request, *args, **kwargs):
        profile = self.get_object()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = self.save_profile_update(profile, serializer)
        return Response(self.get_serializer(profile).data)


class AlumniSearchView(generics.ListAPIView):
    serializer_class = AlumniSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != User.Role.STUDENT:
            raise PermissionDenied("Only students can search the alumni directory.")

        queryset = AlumniProfile.objects.filter(
            verification_status=AlumniProfile.VerificationStatus.VERIFIED
        ).select_related("user")

        company = self.request.query_params.get("company")
        designation = self.request.query_params.get("designation")
        department = self.request.query_params.get("department")
        available = self.request.query_params.get("available")

        if company:
            queryset = queryset.filter(current_company__icontains=company.strip())
        if designation:
            queryset = queryset.filter(designation__icontains=designation.strip())
        if department:
            queryset = queryset.filter(department__icontains=department.strip())
        if available is not None:
            if available.lower() not in {"true", "false"}:
                raise ValidationError({"available": "Use true or false."})
            queryset = queryset.filter(is_open_to_referrals=available.lower() == "true")

        return queryset.order_by("user__username", "id")


def referral_queryset_for_user(user):
    queryset = ReferralRequest.objects.select_related(
        "student",
        "student__student_profile",
        "alumni_profile",
        "alumni_profile__user",
    ).prefetch_related("history__changed_by")

    if user.role == User.Role.STUDENT:
        return queryset.filter(student=user)
    if user.role == User.Role.ALUMNI:
        return queryset.filter(alumni_profile__user=user)
    raise PermissionDenied("Only students and alumni can access referral requests.")


class ReferralRequestListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_referral_request_list",
        responses=ReferralRequestSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        queryset = referral_queryset_for_user(request.user)
        results = ReferralRequestSerializer(queryset, many=True).data
        return Response(results)

    @extend_schema(
        operation_id="alumni_referral_request_create",
        request=ReferralRequestCreateSerializer,
        responses={status.HTTP_201_CREATED: ReferralRequestSerializer},
    )
    def post(self, request, *args, **kwargs):
        if request.user.role != User.Role.STUDENT:
            raise PermissionDenied("Only students can submit referral requests.")

        serializer = ReferralRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        alumni_profile = serializer.context["alumni_profile"]

        try:
            with transaction.atomic():
                referral = ReferralRequest.objects.create(
                    student=request.user,
                    alumni_profile=alumni_profile,
                    opportunity_url=serializer.validated_data["opportunity_url"],
                    resume=serializer.validated_data["resume"],
                    note=serializer.validated_data["note"],
                )
                ReferralRequestHistory.objects.create(
                    referral_request=referral,
                    event=ReferralRequestHistory.Event.REQUESTED,
                    previous_status="",
                    new_status=ReferralRequest.Status.PENDING,
                    changed_by=request.user,
                    note="Referral request submitted.",
                )
                Notification.objects.create(
                    recipient=alumni_profile.user,
                    notification_type=Notification.NotificationType.REFERRAL_REQUEST,
                    title="New student referral request",
                    message=(
                        f"{request.user.get_full_name() or request.user.username} "
                        "has requested a referral."
                    ),
                    referral_request=referral,
                )
        except IntegrityError:
            raise ValidationError({
                "opportunity_url": (
                    "You already have an active referral request to this alumnus "
                    "for this opportunity."
                )
            })

        referral = referral_queryset_for_user(request.user).get(pk=referral.pk)
        return Response(
            ReferralRequestSerializer(referral).data,
            status=status.HTTP_201_CREATED,
        )


class ReferralRequestDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_referral_request_detail",
        responses=ReferralRequestSerializer,
    )
    def get(self, request, pk, *args, **kwargs):
        referral = get_object_or_404(referral_queryset_for_user(request.user), pk=pk)
        return Response(ReferralRequestSerializer(referral).data)


class ReferralRequestActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_referral_request_action",
        request=ReferralRequestActionSerializer,
        responses=ReferralRequestSerializer,
    )
    def post(self, request, pk, action, *args, **kwargs):
        action_serializer = ReferralRequestActionSerializer(data=request.data)
        action_serializer.is_valid(raise_exception=True)
        note = action_serializer.validated_data.get("note", "")

        with transaction.atomic():
            referral = get_object_or_404(
                ReferralRequest.objects.select_for_update().select_related(
                    "student",
                    "alumni_profile__user",
                ),
                pk=pk,
            )
            actor = request.user
            alumni_actions = {"accept", "decline", "request-information", "mark-referred"}

            if action in alumni_actions:
                if (
                    actor.role != User.Role.ALUMNI
                    or referral.alumni_profile.user_id != actor.id
                ):
                    raise PermissionDenied(
                        "Only the assigned alumnus can perform this action."
                    )
            elif action == "respond":
                if actor.role != User.Role.STUDENT or referral.student_id != actor.id:
                    raise PermissionDenied(
                        "Only the student who submitted this request can respond."
                    )
            else:
                raise ValidationError({"action": "Unsupported referral action."})

            previous_status = referral.status
            next_status = previous_status
            event = None
            notification_type = Notification.NotificationType.REFERRAL_STATUS
            notification_recipient = referral.student
            notification_title = "Referral request updated"
            notification_message = ""

            if action == "accept":
                if previous_status != ReferralRequest.Status.PENDING:
                    raise ValidationError({"status": "Only pending requests can be accepted."})
                next_status = ReferralRequest.Status.ACCEPTED
                event = ReferralRequestHistory.Event.ACCEPTED
                notification_message = "Your referral request has been accepted."
            elif action == "decline":
                if previous_status != ReferralRequest.Status.PENDING:
                    raise ValidationError({"status": "Only pending requests can be declined."})
                next_status = ReferralRequest.Status.DECLINED
                event = ReferralRequestHistory.Event.DECLINED
                notification_message = "Your referral request has been declined."
                if note:
                    notification_message += f" Alumni note: {note}"
            elif action == "request-information":
                if previous_status != ReferralRequest.Status.PENDING:
                    raise ValidationError({
                        "status": "More information can only be requested for pending referrals."
                    })
                if len(note) < 10:
                    raise ValidationError({
                        "note": "Provide at least 10 characters describing the information needed."
                    })
                event = ReferralRequestHistory.Event.INFORMATION_REQUESTED
                notification_type = Notification.NotificationType.REFERRAL_MORE_INFO
                notification_title = "More information requested"
                notification_message = f"An alumnus needs more information: {note}"
            elif action == "mark-referred":
                if previous_status != ReferralRequest.Status.ACCEPTED:
                    raise ValidationError({
                        "status": "Only accepted requests can be marked as referred."
                    })
                next_status = ReferralRequest.Status.REFERRED
                event = ReferralRequestHistory.Event.REFERRED
                notification_message = "Your alumnus has marked this referral as completed."
            elif action == "respond":
                if previous_status != ReferralRequest.Status.PENDING:
                    raise ValidationError({
                        "status": "You can only respond while the referral request is pending."
                    })
                latest_event = referral.history.order_by("-created_at", "-id").first()
                if (
                    latest_event is None
                    or latest_event.event != ReferralRequestHistory.Event.INFORMATION_REQUESTED
                ):
                    raise ValidationError({
                        "detail": "The alumnus has not requested additional information."
                    })
                if len(note) < 10:
                    raise ValidationError({
                        "note": "Provide at least 10 characters in your response."
                    })
                event = ReferralRequestHistory.Event.STUDENT_RESPONSE
                notification_recipient = referral.alumni_profile.user
                notification_title = "Student responded to a referral request"
                notification_message = (
                    f"{actor.get_full_name() or actor.username} provided the requested information."
                )

            if next_status != previous_status:
                referral.status = next_status
                referral.save(update_fields=["status", "updated_at"])

            ReferralRequestHistory.objects.create(
                referral_request=referral,
                event=event,
                previous_status=previous_status,
                new_status=next_status,
                changed_by=actor,
                note=note,
            )
            Notification.objects.create(
                recipient=notification_recipient,
                notification_type=notification_type,
                title=notification_title,
                message=notification_message,
                referral_request=referral,
            )

        referral = referral_queryset_for_user(actor).get(pk=referral.pk)
        return Response(ReferralRequestSerializer(referral).data)


class ReferralResumeDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_referral_resume_download",
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request, pk, *args, **kwargs):
        referral = get_object_or_404(referral_queryset_for_user(request.user), pk=pk)
        if not referral.resume or not referral.resume.name:
            raise ValidationError({"resume": "No resume is attached to this referral."})
        return FileResponse(
            referral.resume.open("rb"),
            as_attachment=True,
            filename="student-referral-resume.pdf",
            content_type="application/pdf",
        )


class AlumniEngagementMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_engagement_metrics",
        responses=AlumniEngagementMetricsSerializer,
    )
    def get(self, request, *args, **kwargs):
        if request.user.role != User.Role.ALUMNI:
            raise PermissionDenied("Only alumni can view alumni engagement metrics.")
        profile = get_object_or_404(AlumniProfile, user=request.user)
        requests = ReferralRequest.objects.filter(alumni_profile=profile)
        counts = requests.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=ReferralRequest.Status.PENDING)),
            accepted=Count("id", filter=Q(status=ReferralRequest.Status.ACCEPTED)),
            referred=Count("id", filter=Q(status=ReferralRequest.Status.REFERRED)),
            declined=Count("id", filter=Q(status=ReferralRequest.Status.DECLINED)),
        )
        counts["student_interactions"] = requests.values("student_id").distinct().count()
        counts["is_open_to_referrals"] = profile.is_open_to_referrals
        counts["verification_status"] = profile.verification_status
        return Response(counts)



class AlumniGraduationProofUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="alumni_graduation_proof_upload",
        request=GraduationProofUploadSerializer,
        responses=AlumniProfileSerializer,
    )
    def post(self, request, *args, **kwargs):
        if request.user.role != User.Role.ALUMNI:
            raise PermissionDenied("Only alumni can submit graduation proof.")

        profile = get_object_or_404(AlumniProfile, user=request.user)
        serializer = GraduationProofUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile.graduation_proof = serializer.validated_data["graduation_proof"]
        profile.verification_status = AlumniProfile.VerificationStatus.PENDING
        profile.verification_rejection_reason = ""
        profile.verified_by = None
        profile.verified_at = None
        profile.reviewed_by = None
        profile.reviewed_at = None
        profile.save(
            update_fields=[
                "graduation_proof",
                "verification_status",
                "verification_rejection_reason",
                "verified_by",
                "verified_at",
                "reviewed_by",
                "reviewed_at",
                "updated_at",
            ]
        )
        return Response(AlumniProfileSerializer(profile).data, status=status.HTTP_200_OK)


class PendingAlumniVerificationView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AlumniProfileSerializer

    def get_queryset(self):
        if self.request.user.role != User.Role.IPC_ADMIN:
            raise PermissionDenied("Only IPC administrators can review alumni profiles.")
        return (
            AlumniProfile.objects.filter(
                verification_status=AlumniProfile.VerificationStatus.PENDING,
                graduation_proof__isnull=False,
            )
            .exclude(graduation_proof="")
            .select_related("user")
            .order_by("created_at", "id")
        )


class AlumniGraduationProofDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="ipc_alumni_graduation_proof_download",
        responses=OpenApiTypes.BINARY,
    )
    def get(self, request, pk, *args, **kwargs):
        if request.user.role != User.Role.IPC_ADMIN:
            raise PermissionDenied("Only IPC administrators can view graduation evidence.")
        profile = get_object_or_404(AlumniProfile, pk=pk)
        if not profile.graduation_proof or not profile.graduation_proof.name:
            raise ValidationError({"graduation_proof": "No graduation proof is attached."})
        return FileResponse(
            profile.graduation_proof.open("rb"),
            as_attachment=True,
            filename="alumni-graduation-proof.pdf",
            content_type="application/pdf",
        )


class AlumniVerificationActionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        operation_id="ipc_alumni_verification_action",
        request=AlumniVerificationActionSerializer,
        responses=AlumniProfileSerializer,
    )
    def post(self, request, pk, action, *args, **kwargs):
        if request.user.role != User.Role.IPC_ADMIN:
            raise PermissionDenied("Only IPC administrators can review alumni profiles.")
        serializer = AlumniVerificationActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        with transaction.atomic():
            profile = get_object_or_404(
                AlumniProfile.objects.select_for_update(),
                pk=pk,
            )
            if not profile.graduation_proof or not profile.graduation_proof.name:
                raise ValidationError({"graduation_proof": "Graduation proof is required."})

            now = timezone.now()
            if action == "verify":
                profile.verification_status = AlumniProfile.VerificationStatus.VERIFIED
                profile.verification_rejection_reason = ""
                profile.verified_by = request.user
                profile.verified_at = now
            elif action == "reject":
                if len(reason) < 10:
                    raise ValidationError({
                        "reason": "Provide at least 10 characters explaining the rejection."
                    })
                profile.verification_status = AlumniProfile.VerificationStatus.REJECTED
                profile.verification_rejection_reason = reason
                profile.verified_by = None
                profile.verified_at = None
            else:
                raise ValidationError({"action": "Use verify or reject."})

            profile.reviewed_by = request.user
            profile.reviewed_at = now
            profile.save(
                update_fields=[
                    "verification_status",
                    "verification_rejection_reason",
                    "verified_by",
                    "verified_at",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

        return Response(AlumniProfileSerializer(profile).data, status=status.HTTP_200_OK)


class AlumniVerificationView(APIView):
    """IPC administrator endpoint to review graduation proof and verify/reject an alumnus.

    Enforces that alumni cannot verify themselves, disallows transitions from non-pending,
    requires graduation proof, persists verification metadata, and audits the decision.
    """

    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Verify or reject an alumnus profile",
        description=(
            "Allows authorized IPC administrators to review graduation proof and make a verification "
            "decision for an alumnus profile. Updates verification status, dispatches an audit event, "
            "and prevents unauthorized access."
        ),
        request=AlumniVerificationSerializer,
        responses={
            200: AlumniVerificationResponseSerializer,
            400: {"description": "Invalid decision or disallowed status transition."},
            401: {"description": "Unauthenticated request."},
            403: {"description": "Forbidden: requester lacks IPC administrator role or self-verification."},
            404: {"description": "Alumnus profile not found."},
        },
    )
    def post(self, request, *args, **kwargs):
        if request.user.role != User.Role.IPC_ADMIN:
            raise PermissionDenied("Only IPC administrators can review alumni profiles.")

        lookup_id = kwargs.get("id") or kwargs.get("pk")
        alumni = AlumniProfile.objects.select_related("user").filter(id=lookup_id).first()
        if not alumni:
            return Response(
                {"detail": f"Alumnus profile with id {lookup_id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Business rule: alumni cannot verify themselves
        if alumni.user_id == request.user.id:
            raise PermissionDenied("Alumni cannot verify themselves.")

        # Disallow transition if already decided
        if alumni.verification_status != AlumniProfile.VerificationStatus.PENDING:
            return Response(
                {
                    "detail": (
                        f"Disallowed status transition: alumnus profile for '{alumni.user.username}' "
                        f"is already {alumni.verification_status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AlumniVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        rejection_reason = serializer.validated_data.get("rejection_reason", "")

        now = timezone.now()
        with transaction.atomic():
            alumni.verification_status = new_status
            alumni.verified_by = request.user if new_status == AlumniProfile.VerificationStatus.VERIFIED else None
            alumni.verified_at = now if new_status == AlumniProfile.VerificationStatus.VERIFIED else None
            alumni.reviewed_by = request.user
            alumni.reviewed_at = now
            alumni.verification_rejection_reason = rejection_reason if new_status == AlumniProfile.VerificationStatus.REJECTED else ""
            alumni.save(
                update_fields=[
                    "verification_status",
                    "verification_rejection_reason",
                    "verified_by",
                    "verified_at",
                    "reviewed_by",
                    "reviewed_at",
                    "updated_at",
                ]
            )

            audit.log(
                actor=request.user,
                action=f"ALUMNI_VERIFICATION_{new_status}",
                target=alumni,
                context={
                    "alumnus_user_id": alumni.user_id,
                    "alumnus_username": alumni.user.username,
                    "previous_status": AlumniProfile.VerificationStatus.PENDING,
                    "new_status": new_status,
                    "has_graduation_proof": bool(alumni.graduation_proof),
                    "rejection_reason": rejection_reason,
                },
            )

        proof_url = alumni.graduation_proof.url if (alumni.graduation_proof and hasattr(alumni.graduation_proof, 'url')) else None
        response_data = {
            "id": alumni.id,
            "user_id": alumni.user_id,
            "username": alumni.user.username,
            "verification_status": alumni.verification_status,
            "department": alumni.department,
            "degree_programme": alumni.degree_programme,
            "graduation_year": alumni.graduation_year,
            "graduation_proof": proof_url,
            "rejection_reason": alumni.verification_rejection_reason,
            "verified_by": alumni.verified_by_id,
            "verified_at": alumni.verified_at,
            "updated_at": alumni.updated_at,
        }

        return Response(
            AlumniVerificationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
