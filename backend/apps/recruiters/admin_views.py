"""IPC Administrative views for Nexus Career.

Covers:
- R1: Recruiter and Company Verification
- R2: Opportunity Approval and Rejection (with recruiter notification event & audit)
- R3: Account Suspension and Reactivation
- R4: Audit Trail Views
- R5: Admin Dashboard Metrics
- R6: Activity Reports and Restricted CSV Export
"""

import csv
import io
import json
from datetime import datetime, time, timezone as dt_timezone

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from api.core import audit, events
from api.core.permissions import IsIPCAdmin, IsIPCAdminOrSystemAdmin
from apps.accounts.models import User
from apps.applications.models import Application
from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import OpportunitySerializer

from .models import Company, RecruiterProfile, WorkflowAuditEvent
from .serializers import (
    ActivityReportFilterParamsSerializer,
    ActivityReportItemSerializer,
    AdminDashboardMetricsSerializer,
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


class AdminDashboardMetricsView(APIView):
    """R5: Aggregated metrics dashboard for authorized IPC and System administrators.

    Exposes the 5 core KPI metrics required by SRS §3.8 and the Delivery Plan:
    1. active_opportunities
    2. students
    3. verified_recruiters
    4. applications
    5. pending_approvals
    Plus supportive breakdowns for IPC administrative monitoring.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdminOrSystemAdmin]

    @extend_schema(
        summary="Get IPC Admin Dashboard Metrics",
        description=(
            "Retrieves aggregate placement workflow and platform KPI metrics. "
            "Restricted to authorized IPC and System administrators."
        ),
        responses={
            200: OpenApiResponse(
                response=AdminDashboardMetricsSerializer,
                description="Aggregated platform metrics successfully retrieved.",
            ),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: Requires IPC or System administrator role."),
        },
    )
    def get(self, request, *args, **kwargs):
        now = timezone.now()

        # 1. Active Opportunities: PUBLISHED status with future application deadline
        active_opps_count = Opportunity.objects.filter(
            status=Opportunity.Status.PUBLISHED,
            application_deadline__gt=now,
        ).count()

        # 2. Students: Active student accounts
        students_count = User.objects.filter(
            role=User.Role.STUDENT,
            is_active=True,
        ).count()

        # 3. Verified Recruiters / Companies:
        # Number of recruiters whose associated company is verified, falling back to verified companies
        verified_recruiter_users = User.objects.filter(
            role=User.Role.RECRUITER,
            recruiter_profile__company__verification_status=Company.VerificationStatus.VERIFIED,
        ).count()
        verified_companies_count = Company.objects.filter(
            verification_status=Company.VerificationStatus.VERIFIED,
        ).count()
        verified_recruiters_metric = max(verified_recruiter_users, verified_companies_count)

        # 4. Applications: Total applications submitted across all opportunities
        applications_count = Application.objects.count()

        # 5. Pending Approvals: Opportunities awaiting IPC review
        pending_approvals_count = Opportunity.objects.filter(
            status=Opportunity.Status.PENDING_APPROVAL,
        ).count()

        # Auxiliary breakdowns
        total_opps_count = Opportunity.objects.count()
        pending_companies_count = Company.objects.filter(
            verification_status=Company.VerificationStatus.PENDING,
        ).count()

        try:
            from apps.alumni.models import AlumniProfile
            verified_alumni_count = AlumniProfile.objects.filter(
                verification_status=AlumniProfile.VerificationStatus.VERIFIED,
            ).count()
        except Exception:
            verified_alumni_count = 0

        payload = {
            "active_opportunities": active_opps_count,
            "students": students_count,
            "verified_recruiters": verified_recruiters_metric,
            "applications": applications_count,
            "pending_approvals": pending_approvals_count,
            "total_opportunities": total_opps_count,
            "pending_companies": pending_companies_count,
            "verified_alumni": verified_alumni_count,
        }

        serializer = AdminDashboardMetricsSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


def parse_date_filter(param_str: str, is_end: bool = False) -> datetime:
    """Parses and validates ISO 8601 or YYYY-MM-DD date filter strings."""
    if not param_str or not param_str.strip():
        return None
    val = param_str.strip()
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt
    except ValueError:
        pass

    parts = val.split("-")
    if len(parts) == 3:
        try:
            year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
            t = time.max if is_end else time.min
            return datetime(
                year,
                month,
                day,
                t.hour,
                t.minute,
                t.second,
                t.microsecond if is_end else 0,
                tzinfo=dt_timezone.utc,
            )
        except Exception:
            pass

    raise ValidationError(
        {"detail": f"Invalid date format for '{param_str}'. Expected YYYY-MM-DD or ISO 8601 string."}
    )


def get_filtered_activity_report_items(params) -> list[dict]:
    """Retrieves and unifies activity report items across WorkflowAuditEvent and Application models.

    Supports filtering by:
    - start_date (inclusive UTC)
    - end_date (inclusive UTC)
    - activity_type (OPPORTUNITY, APPLICATION, COMPANY, USER, ALUMNI, or specific action)
    - company (company name substring or company ID)
    - status (PUBLISHED, SUBMITTED, VERIFIED, REJECTED, SUSPENDED, PENDING, etc.)
    """
    start_str = params.get("start_date") or params.get("from_date")
    end_str = params.get("end_date") or params.get("to_date")
    activity_type = (params.get("activity_type") or "").strip()
    company_filter = (params.get("company") or "").strip()
    status_filter = (params.get("status") or "").strip()

    start_dt = parse_date_filter(start_str, is_end=False) if start_str else None
    end_dt = parse_date_filter(end_str, is_end=True) if end_str else None

    if start_dt and end_dt and start_dt > end_dt:
        raise ValidationError({"detail": "start_date cannot be after end_date."})

    items = []

    # 1. Query WorkflowAuditEvent
    audit_qs = WorkflowAuditEvent.objects.select_related("actor").order_by("-created_at")
    if start_dt:
        audit_qs = audit_qs.filter(created_at__gte=start_dt)
    if end_dt:
        audit_qs = audit_qs.filter(created_at__lte=end_dt)

    if activity_type:
        act_upper = activity_type.upper()
        if act_upper in ("OPPORTUNITY", "OPPORTUNITIES"):
            audit_qs = audit_qs.filter(object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY)
        elif act_upper in ("COMPANY", "COMPANIES"):
            audit_qs = audit_qs.filter(object_type=WorkflowAuditEvent.ObjectType.COMPANY)
        elif act_upper in ("USER", "USERS"):
            audit_qs = audit_qs.filter(object_type=WorkflowAuditEvent.ObjectType.USER)
        elif act_upper in ("ALUMNI", "ALUMNUS"):
            audit_qs = audit_qs.filter(object_type=WorkflowAuditEvent.ObjectType.ALUMNI)
        elif act_upper in ("APPLICATION", "APPLICATIONS"):
            audit_qs = audit_qs.none()
        else:
            audit_qs = audit_qs.filter(
                Q(action__icontains=activity_type) | Q(object_type__icontains=activity_type)
            )

    events_list = list(audit_qs[:250])
    company_ids = [e.object_id for e in events_list if e.object_type == WorkflowAuditEvent.ObjectType.COMPANY]
    opp_ids = [e.object_id for e in events_list if e.object_type == WorkflowAuditEvent.ObjectType.OPPORTUNITY]

    companies_map = {c.id: c.name for c in Company.objects.filter(id__in=company_ids)}
    opps_map = {
        o.id: (o.title, o.company.name if o.company else "", o.status)
        for o in Opportunity.objects.filter(id__in=opp_ids).select_related("company")
    }

    for event in events_list:
        comp_name = ""
        st_val = ""
        if event.object_type == WorkflowAuditEvent.ObjectType.COMPANY:
            comp_name = companies_map.get(event.object_id, "") or event.details.get("company_name", "")
            st_val = event.details.get("verification_status", "")
        elif event.object_type == WorkflowAuditEvent.ObjectType.OPPORTUNITY:
            opp_info = opps_map.get(event.object_id)
            if opp_info:
                comp_name = opp_info[1]
                st_val = opp_info[2]
            else:
                comp_name = event.details.get("company_name", "")
                st_val = event.details.get("status", "")
        elif event.object_type == WorkflowAuditEvent.ObjectType.USER:
            st_val = "SUSPENDED" if "SUSPENDED" in event.action else "ACTIVE"
        elif event.object_type == WorkflowAuditEvent.ObjectType.ALUMNI:
            st_val = event.details.get("verification_status", "")

        if not st_val:
            if "APPROVED" in event.action or "VERIFIED" in event.action:
                st_val = "VERIFIED" if "VERIFIED" in event.action else "PUBLISHED"
            elif "REJECTED" in event.action:
                st_val = "REJECTED"
            elif "CREATED" in event.action or "SUBMITTED" in event.action:
                st_val = "PENDING"
            elif "CLOSED" in event.action:
                st_val = "CLOSED"
            elif "ARCHIVED" in event.action:
                st_val = "ARCHIVED"

        if company_filter:
            matches_company = (
                company_filter.lower() in comp_name.lower()
                or (company_filter.isdigit() and event.object_type == "COMPANY" and event.object_id == int(company_filter))
            )
            if not matches_company:
                continue

        if status_filter:
            matches_status = (
                status_filter.lower() == st_val.lower()
                or status_filter.lower() in event.action.lower()
            )
            if not matches_status:
                continue

        items.append({
            "id": f"event-{event.id}",
            "timestamp": event.created_at,
            "activity_type": event.object_type,
            "action": event.action,
            "actor": event.actor.username if event.actor else "System",
            "company": comp_name,
            "target_type": event.object_type,
            "target_id": str(event.object_id),
            "status": st_val,
            "details": event.details or {},
        })

    # 2. Query Applications
    include_applications = True
    if activity_type:
        act_upper = activity_type.upper()
        if act_upper not in ("APPLICATION", "APPLICATIONS", "ALL") and "APP" not in act_upper:
            include_applications = False

    if include_applications:
        app_qs = Application.objects.select_related("student", "opportunity", "opportunity__company").order_by("-submitted_at")
        if start_dt:
            app_qs = app_qs.filter(submitted_at__gte=start_dt)
        if end_dt:
            app_qs = app_qs.filter(submitted_at__lte=end_dt)
        if company_filter:
            if company_filter.isdigit():
                app_qs = app_qs.filter(
                    Q(opportunity__company__id=int(company_filter)) | Q(opportunity__company__name__icontains=company_filter)
                )
            else:
                app_qs = app_qs.filter(opportunity__company__name__icontains=company_filter)
        if status_filter:
            app_qs = app_qs.filter(status__iexact=status_filter)

        for app in app_qs[:250]:
            items.append({
                "id": f"app-{app.id}",
                "timestamp": app.submitted_at,
                "activity_type": "APPLICATION",
                "action": "APPLICATION_SUBMITTED",
                "actor": app.student.username if app.student else "Student",
                "company": app.opportunity.company.name if app.opportunity and app.opportunity.company else "",
                "target_type": "Opportunity",
                "target_id": str(app.opportunity_id),
                "status": app.status,
                "details": {
                    "application_id": app.id,
                    "opportunity_title": app.opportunity.title if app.opportunity else "",
                    "student_username": app.student.username if app.student else "",
                },
            })

    items.sort(key=lambda x: x["timestamp"], reverse=True)
    return items


class ActivityReportListView(APIView):
    """R6: Filterable activity report view for authorized administrators.

    Restricted to IPC and System administrators.
    Supports filtering by date range, activity type, company, and status.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdminOrSystemAdmin]

    @extend_schema(
        summary="List recruitment activity reports",
        description=(
            "Retrieves a paginated list of recruitment activities across the platform. "
            "Supports filtering by date range (start_date, end_date), activity_type, "
            "company, and status. Restricted to IPC and System administrators."
        ),
        parameters=[
            OpenApiParameter(name="start_date", type=str, description="Filter from ISO date (inclusive)."),
            OpenApiParameter(name="end_date", type=str, description="Filter up to ISO date (inclusive)."),
            OpenApiParameter(name="activity_type", type=str, description="Filter by category (OPPORTUNITY, APPLICATION, COMPANY, USER)."),
            OpenApiParameter(name="company", type=str, description="Filter by company name or ID."),
            OpenApiParameter(name="status", type=str, description="Filter by status (PUBLISHED, SUBMITTED, VERIFIED, etc.)."),
            OpenApiParameter(name="page", type=int, description="Page number."),
            OpenApiParameter(name="page_size", type=int, description="Results per page (max 50)."),
        ],
        responses={
            200: OpenApiResponse(response=ActivityReportItemSerializer(many=True)),
            400: OpenApiResponse(description="Invalid filter parameters or date range."),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: Requires IPC or System administrator."),
        },
    )
    def get(self, request, *args, **kwargs):
        items = get_filtered_activity_report_items(request.query_params)
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(items, request)
        serializer = ActivityReportItemSerializer(page if page is not None else items, many=True)
        if page is not None:
            return paginator.get_paginated_response(serializer.data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ActivityReportExportView(APIView):
    """R6: Restricted activity report CSV export endpoint.

    Only authorized IPC or System administrators can export reports.
    Generates a valid RFC 4180 CSV with proper headers, quotes, and UTF-8 encoding.
    Ensures no passwords, tokens, hashes, or sensitive resume contents are leaked.
    Logs every successful export in the shared audit service.
    """

    permission_classes = [permissions.IsAuthenticated, IsIPCAdminOrSystemAdmin]

    @extend_schema(
        summary="Export activity reports to CSV",
        description=(
            "Generates a downloadable CSV export of recruitment activity reports. "
            "Supports filtering by date range (start_date, end_date), activity_type, "
            "company, and status. Restricted to IPC and System administrators. "
            "Every export is recorded in the administrative audit log."
        ),
        parameters=[
            OpenApiParameter(name="start_date", type=str, description="Filter from ISO date (inclusive)."),
            OpenApiParameter(name="end_date", type=str, description="Filter up to ISO date (inclusive)."),
            OpenApiParameter(name="activity_type", type=str, description="Filter by category (OPPORTUNITY, APPLICATION, COMPANY, USER)."),
            OpenApiParameter(name="company", type=str, description="Filter by company name or ID."),
            OpenApiParameter(name="status", type=str, description="Filter by status (PUBLISHED, SUBMITTED, VERIFIED, etc.)."),
        ],
        responses={
            200: OpenApiResponse(description="CSV report file download."),
            400: OpenApiResponse(description="Invalid filter parameters or date range."),
            401: OpenApiResponse(description="Unauthenticated request."),
            403: OpenApiResponse(description="Forbidden: Requires IPC or System administrator."),
        },
    )
    def get(self, request, *args, **kwargs):
        items = get_filtered_activity_report_items(request.query_params)

        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Standard CSV Header row
        writer.writerow([
            "ID",
            "Timestamp (UTC)",
            "Activity Type",
            "Action",
            "Actor",
            "Company",
            "Target Type",
            "Target ID",
            "Status",
            "Details",
        ])

        for item in items:
            ts_str = item["timestamp"].isoformat() if hasattr(item["timestamp"], "isoformat") else str(item["timestamp"])
            safe_details = dict(item.get("details") or {})
            for sensitive_key in ("password", "token", "secret", "hash", "proof_bytes", "resume_bytes"):
                safe_details.pop(sensitive_key, None)
            details_str = json.dumps(safe_details)

            writer.writerow([
                item["id"],
                ts_str,
                item["activity_type"],
                item["action"],
                item["actor"],
                item["company"],
                item["target_type"],
                item["target_id"],
                item["status"],
                details_str,
            ])

        csv_content = output.getvalue()
        output.close()

        # Audit logging of successful export
        now = timezone.now()
        filters_context = {
            "start_date": request.query_params.get("start_date", ""),
            "end_date": request.query_params.get("end_date", ""),
            "activity_type": request.query_params.get("activity_type", ""),
            "company": request.query_params.get("company", ""),
            "status": request.query_params.get("status", ""),
            "record_count": len(items),
        }
        audit.log(
            actor=request.user,
            action="REPORT_EXPORTED",
            target=("REPORT", 0),
            context={
                "format": "csv",
                "filters": filters_context,
                "record_count": len(items),
            },
        )

        filename = f"nexus_career_activity_report_{now.strftime('%Y%m%d_%H%M%S')}.csv"
        response = HttpResponse(csv_content, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

