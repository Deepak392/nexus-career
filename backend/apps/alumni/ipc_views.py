from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.recruiters.permissions import IsIPCAdmin
from apps.recruiters.serializers import RejectionReasonSerializer

from .models import AlumniProfile
from .serializers import AlumniReviewSerializer


class PendingAlumniListView(generics.ListAPIView):
    serializer_class = AlumniReviewSerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def get_queryset(self):
        return (
            AlumniProfile.objects.filter(
                verification_status=AlumniProfile.VerificationStatus.PENDING
            )
            .select_related("user")
            .order_by("created_at")
        )


class AlumniVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @transaction.atomic
    def post(self, request, pk):
        profile = get_object_or_404(
            AlumniProfile.objects.select_for_update().select_related("user"),
            pk=pk,
        )
        if profile.verification_status != AlumniProfile.VerificationStatus.PENDING:
            raise ValidationError({"detail": "Only pending Alumni profiles can be verified."})

        profile.verification_status = AlumniProfile.VerificationStatus.VERIFIED
        profile.verification_rejection_reason = ""
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=[
            "verification_status",
            "verification_rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ])
        Notification.objects.create(
            recipient=profile.user,
            notification_type=Notification.NotificationType.ALUMNI_VERIFICATION,
            title="Alumni profile verified",
            message="Your Alumni profile has been verified. You can now appear in the student Alumni directory when referral availability is enabled.",
        )
        return Response(AlumniReviewSerializer(profile).data)


class AlumniRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @transaction.atomic
    def post(self, request, pk):
        profile = get_object_or_404(
            AlumniProfile.objects.select_for_update().select_related("user"),
            pk=pk,
        )
        if profile.verification_status != AlumniProfile.VerificationStatus.PENDING:
            raise ValidationError({"detail": "Only pending Alumni profiles can be rejected."})

        serializer = RejectionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]

        profile.verification_status = AlumniProfile.VerificationStatus.REJECTED
        profile.verification_rejection_reason = reason
        profile.reviewed_by = request.user
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=[
            "verification_status",
            "verification_rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "updated_at",
        ])
        Notification.objects.create(
            recipient=profile.user,
            notification_type=Notification.NotificationType.ALUMNI_VERIFICATION,
            title="Alumni profile needs attention",
            message=f"Your Alumni profile was not verified. IPC feedback: {reason}",
        )
        return Response(AlumniReviewSerializer(profile).data)
