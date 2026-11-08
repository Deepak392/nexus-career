from django.utils import timezone
from rest_framework import viewsets

from .models import Opportunity
from .serializers import OpportunitySerializer


class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """Public discovery exposes published opportunities before their deadlines."""

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        return (
            Opportunity.objects.filter(
                status=Opportunity.Status.PUBLISHED,
                application_deadline__gt=timezone.now(),
            )
            .select_related("company", "created_by")
            .order_by("-published_at", "-created_at")
        )
