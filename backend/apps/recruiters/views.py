from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.opportunities.models import Opportunity
from apps.opportunities.serializers import RecruiterOpportunitySerializer

from .models import Company, RecruiterProfile, WorkflowAuditEvent
from .permissions import IsRecruiter
from .serializers import CompanyProfileSerializer


class CompanyProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]

    @staticmethod
    def get_profile(user):
        try:
            return user.recruiter_profile
        except RecruiterProfile.DoesNotExist:
            return None

    def get(self, request):
        profile = self.get_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "Create a company profile first."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CompanyProfileSerializer(profile.company).data)

    @transaction.atomic
    def post(self, request):
        if self.get_profile(request.user) is not None:
            raise ValidationError(
                {"detail": "Your recruiter account already has a company profile."}
            )
        serializer = CompanyProfileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        company = serializer.save(
            verification_status=Company.VerificationStatus.PENDING
        )
        RecruiterProfile.objects.create(
            user=request.user,
            company=company,
            work_email=company.contact_email,
            contact_phone=company.contact_phone,
        )
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.COMPANY,
            object_id=company.pk,
            action=WorkflowAuditEvent.Action.COMPANY_CREATED,
        )
        return Response(
            CompanyProfileSerializer(company).data,
            status=status.HTTP_201_CREATED,
        )

    @transaction.atomic
    def patch(self, request):
        profile = self.get_profile(request.user)
        if profile is None:
            return Response(
                {"detail": "Create a company profile first."},
                status=status.HTTP_404_NOT_FOUND,
            )
        company = profile.company
        serializer = CompanyProfileSerializer(
            company,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        company = serializer.save()

        # Company details must be reviewed again after a profile change.
        company.verification_status = Company.VerificationStatus.PENDING
        company.verification_rejection_reason = ""
        company.verified_by = None
        company.verified_at = None
        company.reviewed_by = None
        company.reviewed_at = None
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
            action=WorkflowAuditEvent.Action.COMPANY_PROFILE_UPDATED,
        )
        return Response(CompanyProfileSerializer(company).data)


class RecruiterOpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = RecruiterOpportunitySerializer
    permission_classes = [permissions.IsAuthenticated, IsRecruiter]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_recruiter_profile(self):
        try:
            return self.request.user.recruiter_profile
        except RecruiterProfile.DoesNotExist:
            return None

    def get_queryset(self):
        profile = self.get_recruiter_profile()
        if profile is None:
            return Opportunity.objects.none()
        return (
            Opportunity.objects.filter(company=profile.company)
            .select_related("company", "created_by", "approved_by")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        profile = self.get_recruiter_profile()
        if profile is None:
            raise ValidationError(
                {"detail": "Create a company profile before posting opportunities."}
            )
        serializer.save(
            company=profile.company,
            created_by=self.request.user,
            status=Opportunity.Status.DRAFT,
        )

    def perform_update(self, serializer):
        opportunity = serializer.instance
        if opportunity.status not in {
            Opportunity.Status.DRAFT,
            Opportunity.Status.REJECTED,
        }:
            raise ValidationError(
                {"detail": "Only draft or rejected opportunities can be edited."}
            )
        if opportunity.status == Opportunity.Status.REJECTED:
            serializer.save(
                status=Opportunity.Status.DRAFT,
                rejection_reason="",
                approved_by=None,
                approved_at=None,
                published_at=None,
            )
        else:
            serializer.save()

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        opportunity = self.get_object()
        if opportunity.status not in {
            Opportunity.Status.DRAFT,
            Opportunity.Status.REJECTED,
        }:
            raise ValidationError(
                {"detail": "Only draft or rejected opportunities can be submitted."}
            )
        if opportunity.company.verification_status != Company.VerificationStatus.VERIFIED:
            raise ValidationError(
                {"detail": "The company must be verified before submitting an opportunity."}
            )
        if opportunity.application_deadline <= timezone.now():
            raise ValidationError(
                {"application_deadline": "The application deadline must be in the future."}
            )

        opportunity.status = Opportunity.Status.PENDING_APPROVAL
        opportunity.rejection_reason = ""
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
            action=WorkflowAuditEvent.Action.OPPORTUNITY_SUBMITTED,
        )
        return Response(self.get_serializer(opportunity).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        opportunity = self.get_object()
        if opportunity.status != Opportunity.Status.PUBLISHED:
            raise ValidationError(
                {"detail": "Only published opportunities can be closed."}
            )
        opportunity.status = Opportunity.Status.CLOSED
        opportunity.save(update_fields=["status", "updated_at"])
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY,
            object_id=opportunity.pk,
            action=WorkflowAuditEvent.Action.OPPORTUNITY_CLOSED,
        )
        return Response(self.get_serializer(opportunity).data)

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        allowed = {
            Opportunity.Status.DRAFT,
            Opportunity.Status.REJECTED,
            Opportunity.Status.CLOSED,
        }
        opportunity = self.get_object()
        if opportunity.status not in allowed:
            raise ValidationError(
                {"detail": "Only draft, rejected or closed opportunities can be archived."}
            )
        opportunity.status = Opportunity.Status.ARCHIVED
        opportunity.save(update_fields=["status", "updated_at"])
        WorkflowAuditEvent.objects.create(
            actor=request.user,
            object_type=WorkflowAuditEvent.ObjectType.OPPORTUNITY,
            object_id=opportunity.pk,
            action=WorkflowAuditEvent.Action.OPPORTUNITY_ARCHIVED,
        )
        return Response(self.get_serializer(opportunity).data)
