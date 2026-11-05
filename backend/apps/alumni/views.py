from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, mixins, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from api.core.audit import log_verification_audit
from api.core.permissions import IsIPCAdmin
from apps.accounts.models import User
from .models import AlumniProfile
from .serializers import (
    AlumniProfileSerializer,
    AlumniSearchSerializer,
    AlumniVerificationResponseSerializer,
    AlumniVerificationSerializer,
)


class AlumniProfileView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):

    serializer_class = AlumniProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_alumni_role(self):
        if self.request.user.role != User.Role.ALUMNI:
            raise PermissionDenied(
                "Only alumni can access alumni profiles."
            )

    def get_object(self):
        self.check_alumni_role()
        return get_object_or_404(
            AlumniProfile,
            user=self.request.user,
        )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.check_alumni_role()

        if AlumniProfile.objects.filter(user=request.user).exists():
            raise ValidationError(
                {"detail": "You already have an alumni profile."}
            )

        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AlumniSearchView(generics.ListAPIView):
    serializer_class = AlumniSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = AlumniProfile.objects.filter(
            verification_status=AlumniProfile.VerificationStatus.VERIFIED
        )

        company = self.request.query_params.get("company")
        designation = self.request.query_params.get("designation")
        department = self.request.query_params.get("department")

        if company:
            queryset = queryset.filter(
                current_company__icontains=company
            )

        if designation:
            queryset = queryset.filter(
                designation__icontains=designation
            )

        if department:
            queryset = queryset.filter(
                department__icontains=department
            )

        return queryset.order_by("id")


class AlumniVerificationView(APIView):
    """IPC administrator endpoint to review graduation proof and verify/reject an alumnus."""

    permission_classes = [IsIPCAdmin]

    @extend_schema(
        summary="Verify or reject an alumnus profile",
        description=(
            "Allows authorized IPC administrators to review graduation proof and make a verification "
            "decision for an alumnus profile. Updates verification status, dispatches an audit event, "
            "and prevents unauthorized access."
        ),
        request=AlumniVerificationSerializer,
        responses={
            200: OpenApiResponse(
                response=AlumniVerificationResponseSerializer,
                description="Alumnus verification decision successfully recorded.",
            ),
            400: OpenApiResponse(description="Invalid decision or disallowed status transition."),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: requester lacks IPC administrator role."),
            404: OpenApiResponse(description="Alumnus profile not found."),
        },
    )
    def post(self, request, id):
        alumni = AlumniProfile.objects.select_related("user").filter(id=id).first()
        if not alumni:
            return Response(
                {"detail": f"Alumnus profile with id {id} not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

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

        with transaction.atomic():
            alumni.verification_status = new_status
            alumni.updated_at = timezone.now()
            alumni.save(update_fields=["verification_status", "updated_at"])

            log_verification_audit(
                actor=request.user,
                action=f"ALUMNI_VERIFICATION_{new_status}",
                target_type="AlumniProfile",
                target_id=alumni.id,
                details={
                    "alumnus_user_id": alumni.user_id,
                    "alumnus_username": alumni.user.username,
                    "previous_status": AlumniProfile.VerificationStatus.PENDING,
                    "new_status": new_status,
                    "has_graduation_proof": bool(alumni.graduation_proof),
                    "rejection_reason": rejection_reason,
                },
            )

        response_data = {
            "id": alumni.id,
            "user_id": alumni.user_id,
            "username": alumni.user.username,
            "verification_status": alumni.verification_status,
            "department": alumni.department,
            "degree_programme": alumni.degree_programme,
            "graduation_year": alumni.graduation_year,
            "graduation_proof": alumni.graduation_proof.url if alumni.graduation_proof else None,
            "rejection_reason": rejection_reason,
            "updated_at": alumni.updated_at,
        }

        return Response(
            AlumniVerificationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
