"""IPC Administrative views for Nexus Career.

Covers:
- R1: Recruiter and Company Verification
- R2: Opportunity Approval and Rejection (with recruiter notification event & audit)
- R3: Account Suspension and Reactivation
- R4: Audit Trail Views
"""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from api.core import audit, events
from api.core.permissions import IsIPCAdmin, IsIPCAdminOrSystemAdmin
from apps.accounts.models import User
from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import OpportunitySerializer

from .models import Company, RecruiterProfile, WorkflowAuditEvent
from .serializers import (
    AuditLogEntrySerializer,
    CompanyProfileSerializer,
    RecruiterVerificationResponseSerializer,
    RecruiterVerificationSerializer,
    RejectionReasonSerializer,
    UserAccountActionResponseSerializer,
    UserSuspensionSerializer,
)


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50


class PendingCompanyListView(generics.ListAPIView):
    """Lists companies pending IPC verification."""

    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def get_queryset(self):
        return Company.objects.filter(
            verification_status=Company.VerificationStatus.PENDING
        ).order_by("created_at")


class RecruiterVerificationView(APIView):
    """IPC administrator endpoint to verify or reject a recruiter and their associated company.

    Enforces that email verification alone does not verify a company, recruiters cannot
    verify themselves or other companies, and audit logging is recorded.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(
        summary="Verify or reject a recruiter / company",
        description=(
            "Allows authorized IPC administrators to review and make a verification decision "
            "for an eligible recruiter. Updates the company verification status, records the acting "
            "administrator and timestamp, and logs an audit record."
        ),
        request=RecruiterVerificationSerializer,
        responses={
            200: OpenApiResponse(
                response=RecruiterVerificationResponseSerializer,
                description="Verification decision successfully recorded.",
            ),
            400: OpenApiResponse(description="Invalid verification status or disallowed status transition."),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: requester lacks IPC administrator role or self-verification."),
            404: OpenApiResponse(description="Recruiter or associated company not found."),
        },
    )
    def post(self, request, *args, **kwargs):
        lookup_id = kwargs.get("id") or kwargs.get("pk")
        recruiter = RecruiterProfile.objects.select_related("user", "company").filter(id=lookup_id).first()
        if not recruiter:
            company = Company.objects.filter(id=lookup_id).first()
            if not company:
                return Response(
                    {"detail": f"Recruiter or company with id {lookup_id} not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            recruiter = RecruiterProfile.objects.select_related("user", "company").filter(company=company).first()
        else:
            company = recruiter.company

        # Business rule: recruiter cannot verify themselves
        if recruiter and recruiter.user_id == request.user.id:
            raise PermissionDenied("A recruiter cannot verify themselves.")

        # Business rule: only PENDING companies can transition
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
            company.verified_by = request.user if new_status == Company.VerificationStatus.VERIFIED else None
            company.verified_at = now if new_status == Company.VerificationStatus.VERIFIED else None
            company.reviewed_by = request.user
            company.reviewed_at = now
            company.verification_rejection_reason = rejection_reason if new_status == Company.VerificationStatus.REJECTED else ""
            company.save(
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

            # Record in shared audit service
            audit.log(
                actor=request.user,
                action=f"RECRUITER_VERIFICATION_{new_status}",
                target=company,
                context={
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
            "verified_by": company.verified_by_id,
            "verified_at": company.verified_at,
            "rejection_reason": company.verification_rejection_reason,
        }

        return Response(
            RecruiterVerificationResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )


class CompanyVerifyView(APIView):
    """IPC endpoint to verify a company directly by primary key."""

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(request=None, responses=CompanyProfileSerializer)
    @transaction.atomic
    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        if company.verification_status == Company.VerificationStatus.VERIFIED:
            raise ValidationError({"detail": "Company is already verified."})

        now = timezone.now()
        company.verification_status = Company.VerificationStatus.VERIFIED
        company.verification_rejection_reason = ""
        company.verified_by = request.user
        company.verified_at = now
        company.reviewed_by = request.user
        company.reviewed_at = now
        company.save(
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
            action="COMPANY_VERIFIED",
            target=company,
            context={"company_name": company.name},
        )
        return Response(CompanyProfileSerializer(company).data)


class CompanyRejectView(APIView):
    """IPC endpoint to reject a company directly by primary key."""

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(
        request=RejectionReasonSerializer,
        responses=CompanyProfileSerializer,
    )
    @transaction.atomic
    def post(self, request, pk):
        company = get_object_or_404(Company, pk=pk)
        if company.verification_status == Company.VerificationStatus.VERIFIED:
            raise ValidationError(
                {"detail": "A verified company cannot be rejected without a new review."}
            )

        serializer = RejectionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
        now = timezone.now()
        company.verification_status = Company.VerificationStatus.REJECTED
        company.verification_rejection_reason = reason
        company.verified_by = None
        company.verified_at = None
        company.reviewed_by = request.user
        company.reviewed_at = now
        company.save(
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
            action="COMPANY_REJECTED",
            target=company,
            context={"company_name": company.name, "reason": reason},
        )
        return Response(CompanyProfileSerializer(company).data)


class PendingOpportunityListView(generics.ListAPIView):
    """Lists opportunities waiting for IPC approval."""

    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def get_queryset(self):
        return (
            Opportunity.objects.filter(status=Opportunity.Status.PENDING_APPROVAL)
            .select_related("company", "created_by")
            .order_by("created_at")
        )


class OpportunityApproveView(APIView):
    """R2: Approves a pending opportunity and emits recruiter notification event."""

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(request=None, responses=OpportunitySerializer)
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("id") or kwargs.get("pk")
        opportunity = get_object_or_404(
            Opportunity.objects.select_related("company", "created_by"),
            pk=pk,
        )
        if opportunity.status != Opportunity.Status.PENDING_APPROVAL:
            raise ValidationError(
                {"detail": "Only pending opportunities can be approved."}
            )
        if opportunity.company.verification_status != Company.VerificationStatus.VERIFIED:
            raise ValidationError(
                {"detail": "The opportunity's company must be verified before approval."}
            )
        if opportunity.application_deadline <= timezone.now():
            raise ValidationError(
                {"application_deadline": "Expired opportunities cannot be published."}
            )

        now = timezone.now()
        opportunity.status = Opportunity.Status.PUBLISHED
        opportunity.approved_by = request.user
        opportunity.approved_at = now
        opportunity.published_at = now
        opportunity.rejection_reason = ""
        opportunity.save(
            update_fields=[
                "status",
                "approved_by",
                "approved_at",
                "published_at",
                "rejection_reason",
                "updated_at",
            ]
        )

        # Audit administrative action
        audit.log(
            actor=request.user,
            action="OPPORTUNITY_APPROVED",
            target=opportunity,
            context={
                "title": opportunity.title,
                "company_id": opportunity.company_id,
                "company_name": opportunity.company.name,
            },
        )

        # Emit recruiter notification event
        events.emit(
            event_type="OPPORTUNITY_APPROVED",
            payload={
                "opportunity_id": opportunity.id,
                "opportunity_title": opportunity.title,
                "recipient_id": opportunity.created_by_id,
                "decision": "APPROVED",
                "company_id": opportunity.company_id,
            },
        )

        return Response(OpportunitySerializer(opportunity).data, status=status.HTTP_200_OK)


class OpportunityRejectView(APIView):
    """R2: Rejects a pending opportunity with mandatory reason and emits recruiter event."""

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(
        request=RejectionReasonSerializer,
        responses=OpportunitySerializer,
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        pk = kwargs.get("id") or kwargs.get("pk")
        opportunity = get_object_or_404(
            Opportunity.objects.select_related("created_by", "company"),
            pk=pk,
        )
        if opportunity.status != Opportunity.Status.PENDING_APPROVAL:
            raise ValidationError(
                {"detail": "Only pending opportunities can be rejected."}
            )

        # Accept either 'reason' or 'rejection_reason'
        reason = request.data.get("reason") or request.data.get("rejection_reason")
        if not reason or len(str(reason).strip()) < 5:
            raise ValidationError(
                {"reason": "A valid rejection reason (minimum 5 characters) is required."}
            )
        reason = str(reason).strip()

        opportunity.status = Opportunity.Status.REJECTED
        opportunity.rejection_reason = reason
        opportunity.approved_by = None
        opportunity.approved_at = None
        opportunity.published_at = None
        opportunity.save(
            update_fields=[
                "status",
                "rejection_reason",
                "approved_by",
                "approved_at",
                "published_at",
                "updated_at",
            ]
        )

        # Record audit log
        audit.log(
            actor=request.user,
            action="OPPORTUNITY_REJECTED",
            target=opportunity,
            context={
                "title": opportunity.title,
                "company_id": opportunity.company_id,
                "company_name": opportunity.company.name,
                "reason": reason,
            },
        )

        # Emit recruiter notification event
        events.emit(
            event_type="OPPORTUNITY_REJECTED",
            payload={
                "opportunity_id": opportunity.id,
                "opportunity_title": opportunity.title,
                "recipient_id": opportunity.created_by_id,
                "decision": "REJECTED",
                "reason": reason,
                "company_id": opportunity.company_id,
            },
        )

        return Response(OpportunitySerializer(opportunity).data, status=status.HTTP_200_OK)


class UserSuspendView(APIView):
    """R3: Suspends an active user account.

    Restricted to authorized IPC administrators.
    Enforces that administrators cannot suspend themselves, IPC admins cannot suspend
    System Admins, and already suspended users return 400.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(
        summary="Suspend user account",
        request=UserSuspensionSerializer,
        responses={
            200: OpenApiResponse(response=UserAccountActionResponseSerializer),
            400: OpenApiResponse(description="Disallowed self-suspension or user already suspended."),
            403: OpenApiResponse(description="Forbidden action on protected administrator account."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user_id = kwargs.get("id") or kwargs.get("pk")
        target_user = get_object_or_404(User, pk=user_id)

        # Business rule: cannot suspend oneself
        if target_user.pk == request.user.pk:
            raise ValidationError({"detail": "Administrators cannot suspend their own account."})

        # Business rule: IPC admin cannot suspend System Admin
        if target_user.role == User.Role.SYSTEM_ADMIN and request.user.role != User.Role.SYSTEM_ADMIN:
            raise PermissionDenied("IPC administrators cannot suspend System Administrator accounts.")

        # Business rule: account must be currently active
        if not target_user.is_active:
            raise ValidationError({"detail": "User account is already suspended."})

        serializer = UserSuspensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get("reason", "")

        target_user.is_active = False
        target_user.save(update_fields=["is_active", "updated_at"])

        now = timezone.now()
        audit.log(
            actor=request.user,
            action="USER_SUSPENDED",
            target=target_user,
            context={
                "target_username": target_user.username,
                "target_role": target_user.role,
                "reason": reason,
            },
        )

        response_data = {
            "id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role,
            "is_active": target_user.is_active,
            "is_verified": target_user.is_verified,
            "action": "SUSPENDED",
            "performed_by": request.user.id,
            "timestamp": now,
            "reason": reason,
        }

        return Response(
            UserAccountActionResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )


class UserReactivateView(APIView):
    """R3: Reactivates a suspended user account.

    Restricted to authorized IPC administrators.
    Reactivation of an active (non-suspended) account returns 400.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    @extend_schema(
        summary="Reactivate suspended user account",
        request=None,
        responses={
            200: OpenApiResponse(response=UserAccountActionResponseSerializer),
            400: OpenApiResponse(description="User is not currently suspended."),
            403: OpenApiResponse(description="Forbidden action."),
            404: OpenApiResponse(description="User not found."),
        },
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user_id = kwargs.get("id") or kwargs.get("pk")
        target_user = get_object_or_404(User, pk=user_id)

        # Business rule: account must be currently suspended
        if target_user.is_active:
            raise ValidationError({"detail": "User account is not suspended."})

        target_user.is_active = True
        target_user.save(update_fields=["is_active", "updated_at"])

        now = timezone.now()
        audit.log(
            actor=request.user,
            action="USER_REACTIVATED",
            target=target_user,
            context={
                "target_username": target_user.username,
                "target_role": target_user.role,
            },
        )

        response_data = {
            "id": target_user.id,
            "username": target_user.username,
            "email": target_user.email,
            "role": target_user.role,
            "is_active": target_user.is_active,
            "is_verified": target_user.is_verified,
            "action": "REACTIVATED",
            "performed_by": request.user.id,
            "timestamp": now,
            "reason": "",
        }

        return Response(
            UserAccountActionResponseSerializer(response_data).data,
            status=status.HTTP_200_OK,
        )


class AuditLogListView(generics.ListAPIView):
    """R4: Authorized audit trail viewing API.

    Restricted to authorized IPC or System administrators.
    Exposes actor, action, target, and timestamp without leaking secrets.
    Supports filtering by action, target_type, and actor username.
    """

    serializer_class = AuditLogEntrySerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdminOrSystemAdmin]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = WorkflowAuditEvent.objects.select_related("actor").order_by("-created_at")

        if not hasattr(self, "request") or not self.request:
            return queryset

        action_filter = self.request.query_params.get("action")
        if action_filter:
            queryset = queryset.filter(action__iexact=action_filter.strip())

        target_type_filter = self.request.query_params.get("target_type")
        if target_type_filter:
            queryset = queryset.filter(object_type__iexact=target_type_filter.strip())

        actor_filter = self.request.query_params.get("actor")
        if actor_filter:
            val = actor_filter.strip()
            if val.isdigit():
                queryset = queryset.filter(actor_id=int(val))
            else:
                queryset = queryset.filter(actor__username__icontains=val)

        return queryset

    @extend_schema(
        summary="List audit log events",
        responses={200: OpenApiResponse(response=AuditLogEntrySerializer(many=True))},
    )
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        items = page if page is not None else queryset

        results = []
        for event in items:
            results.append({
                "id": event.id,
                "actor": {
                    "id": event.actor.id,
                    "username": event.actor.username,
                    "email": event.actor.email,
                    "role": event.actor.role,
                },
                "action": event.action,
                "target_type": event.object_type,
                "target_id": event.object_id,
                "target": f"{event.object_type}:{event.object_id}",
                "details": event.details or {},
                "created_at": event.created_at,
            })

        if page is not None:
            return self.get_paginated_response(results)
        return Response(results, status=status.HTTP_200_OK)
