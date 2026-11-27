from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.applications.models import Application
from apps.students.models import StudentProfile
from apps.students.permissions import IsStudent

from .eligibility import evaluate_eligibility
from .models import Opportunity
from .serializers import OpportunitySerializer


class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """Public discovery exposes published, unexpired opportunities only."""

    serializer_class = OpportunitySerializer
    ordering_aliases = {
        "newest": "-published_at",
        "deadline": "application_deadline",
        "title": "title",
        "-title": "-title",
    }

    def get_queryset(self):
        queryset = (
            Opportunity.objects.filter(
                status=Opportunity.Status.PUBLISHED,
                application_deadline__gt=timezone.now(),
            )
            .select_related("company", "created_by")
        )

        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.annotate(
                searchable_skills=Cast("required_skills", output_field=TextField())
            ).filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(company__name__icontains=search)
                | Q(location__icontains=search)
                | Q(searchable_skills__icontains=search)
            )

        opportunity_type = self.request.query_params.get("opportunity_type")
        if opportunity_type:
            queryset = queryset.filter(opportunity_type=opportunity_type)

        work_mode = self.request.query_params.get("work_mode")
        if work_mode:
            queryset = queryset.filter(work_mode=work_mode)

        location = self.request.query_params.get("location", "").strip()
        if location:
            queryset = queryset.filter(location__icontains=location)

        application_method = self.request.query_params.get("application_method")
        if application_method:
            queryset = queryset.filter(application_method=application_method)

        ordering = self.request.query_params.get("ordering", "newest")
        queryset = queryset.order_by(
            self.ordering_aliases.get(ordering, "-published_at"),
            "-created_at",
        )
        return queryset


class OpportunityEligibilityView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsStudent]

    @extend_schema(
        description=(
            "Compare the authenticated student's profile with the published "
            "opportunity criteria. Missing information is returned separately "
            "from unmet requirements."
        ),
        responses={
            200: inline_serializer(
                name="OpportunityEligibilityResult",
                fields={
                    "status": serializers.ChoiceField(
                        choices=["ELIGIBLE", "INELIGIBLE", "INCOMPLETE_PROFILE"]
                    ),
                    "eligible": serializers.BooleanField(allow_null=True),
                    "checks": serializers.ListField(child=serializers.DictField()),
                    "reasons": serializers.ListField(child=serializers.CharField()),
                    "missing_fields": serializers.ListField(child=serializers.CharField()),
                    "has_resume": serializers.BooleanField(),
                    "resume_required": serializers.BooleanField(),
                    "application_method": serializers.ChoiceField(choices=["PLATFORM", "EXTERNAL"]),
                    "external_application_url": serializers.CharField(allow_blank=True),
                    "ready_to_apply": serializers.BooleanField(),
                    "resume_message": serializers.CharField(allow_blank=True),
                    "already_applied": serializers.BooleanField(),
                },
            )
        },
    )
    def get(self, request, pk):
        opportunity = get_object_or_404(
            Opportunity.objects.select_related("company"),
            pk=pk,
            status=Opportunity.Status.PUBLISHED,
            application_deadline__gt=timezone.now(),
        )
        profile = StudentProfile.objects.filter(user=request.user).first()
        result = evaluate_eligibility(opportunity, profile)
        has_resume = bool(profile and profile.has_resume)
        external = opportunity.application_method == "EXTERNAL"
        already_applied = (
            False
            if external
            else Application.objects.filter(
                student=request.user,
                opportunity=opportunity,
            ).exists()
        )

        return Response(
            {
                **result,
                "has_resume": has_resume,
                "resume_required": not external,
                "application_method": opportunity.application_method,
                "external_application_url": (
                    opportunity.external_application_url if external else ""
                ),
                "ready_to_apply": (
                    result["eligible"] is True
                    and (external or has_resume)
                    and not already_applied
                ),
                "resume_message": (
                    ""
                    if external or has_resume
                    else "Upload a PDF resume in your student profile before applying."
                ),
                "already_applied": already_applied,
            },
            status=status.HTTP_200_OK,
        )
