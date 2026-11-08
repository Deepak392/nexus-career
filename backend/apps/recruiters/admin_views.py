from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import OpportunitySerializer

from .models import Company, WorkflowAuditEvent
from .permissions import IsIPCAdmin
from .serializers import CompanyProfileSerializer, RejectionReasonSerializer


class PendingCompanyListView(generics.ListAPIView):
    serializer_class = CompanyProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def get_queryset(self):
        return Company.objects.filter(
            verification_status=Company.VerificationStatus.PENDING
        ).order_by("created_at")


class CompanyVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

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
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=company.pk,
            action=WorkflowAuditEvent.Action.COMPANY_VERIFIED,
        )
        return Response(CompanyProfileSerializer(company).data)


class CompanyRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

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
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=company.pk,
            action=WorkflowAuditEvent.Action.COMPANY_REJECTED,
            details={"reason": reason},
        )
        return Response(CompanyProfileSerializer(company).data)


class PendingOpportunityListView(generics.ListAPIView):
    serializer_class = OpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def get_queryset(self):
        return (
            Opportunity.objects.filter(status=Opportunity.Status.PENDING_APPROVAL)
            .select_related("company", "created_by")
            .order_by("created_at")
        )


class OpportunityApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def post(self, request, pk):
        opportunity = get_object_or_404(
            Opportunity.objects.select_related("company"),
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
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY,
            object_id=opportunity.pk,
            action=WorkflowAuditEvent.Action.OPPORTUNITY_APPROVED,
        )
        return Response(OpportunitySerializer(opportunity).data)


class OpportunityRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsIPCAdmin]

    def post(self, request, pk):
        opportunity = get_object_or_404(Opportunity, pk=pk)
        if opportunity.status != Opportunity.Status.PENDING_APPROVAL:
            raise ValidationError(
                {"detail": "Only pending opportunities can be rejected."}
            )
        serializer = RejectionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"]
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
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY,
            object_id=opportunity.pk,
            action=WorkflowAuditEvent.Action.OPPORTUNITY_REJECTED,
            details={"reason": reason},
        )
        return Response(OpportunitySerializer(opportunity).data)
