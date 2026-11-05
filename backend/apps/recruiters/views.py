from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.core.audit import log_verification_audit
from api.core.permissions import IsIPCAdmin
from .models import Company, RecruiterProfile
from .serializers import (
    RecruiterVerificationResponseSerializer,
    RecruiterVerificationSerializer,
)


class RecruiterVerificationView(APIView):
    """IPC administrator endpoint to verify or reject a recruiter/company."""

    permission_classes = [IsIPCAdmin]

    @extend_schema(
        summary="Verify or reject a recruiter / company",
        description=(
            "Allows authorized IPC administrators to review and make a verification decision "
            "for an eligible recruiter. The associated company verification status is updated, "
            "the acting administrator and timestamp are recorded, and an audit event is dispatched."
        ),
        request=RecruiterVerificationSerializer,
        responses={
            200: OpenApiResponse(
                response=RecruiterVerificationResponseSerializer,
                description="Verification decision successfully recorded.",
            ),
            400: OpenApiResponse(description="Invalid verification status or disallowed status transition."),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: requester lacks IPC administrator role."),
            404: OpenApiResponse(description="Recruiter or associated company not found."),
        },
    )
    def post(self, request, id):
        # Look up RecruiterProfile first by id, or fallback to Company id
        recruiter = RecruiterProfile.objects.select_related("user", "company").filter(id=id).first()
        if not recruiter:
            company = Company.objects.filter(id=id).first()
            if not company:
                return Response(
                    {"detail": f"Recruiter or company with id {id} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            recruiter = RecruiterProfile.objects.select_related("user", "company").filter(company=company).first()
        else:
            company = recruiter.company

        # Validate that the company is currently PENDING
        if company.verification_status != Company.VerificationStatus.PENDING:
            return Response(
                {
                    "detail": (
                        f"Disallowed status transition: company '{company.name}' "
                        f"is already {company.verification_status}."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = RecruiterVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        rejection_reason = serializer.validated_data.get("rejection_reason", "")

        now = timezone.now()

        with transaction.atomic():
            company.verification_status = new_status
            company.verified_by = request.user
            company.verified_at = now
            company.save(update_fields=["verification_status", "verified_by", "verified_at", "updated_at"])

            # Dispatch audit event
            log_verification_audit(
                actor=request.user,
                action=f"RECRUITER_VERIFICATION_{new_status}",
                target_type="Company",
                target_id=company.id,
                details={
                    "company_name": company.name,
                    "recruiter_id": recruiter.id if recruiter else None,
                    "recruiter_username": recruiter.user.username if recruiter else None,
                    "previous_status": Company.VerificationStatus.PENDING,
                    "new_status": new_status,
                    "rejection_reason": rejection_reason,
                },
            )

        response_data = {
            "id": recruiter.id if recruiter else company.id,
            "recruiter_username": recruiter.user.username if recruiter else "",
            "company_id": company.id,
            "company_name": company.name,
            "verification_status": company.verification_status,
            "verified_by": request.user.id,
            "verified_at": company.verified_at,
            "rejection_reason": rejection_reason,
        }

        return Response(
            RecruiterVerificationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )
