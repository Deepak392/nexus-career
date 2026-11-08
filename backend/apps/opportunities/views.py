from django.db.models import Q, TextField
from django.db.models.functions import Cast
from django.utils import timezone
from rest_framework import viewsets

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
                searchable_skills=Cast(
                    "required_skills",
                    output_field=TextField(),
                )
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
