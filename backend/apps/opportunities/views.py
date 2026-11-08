from django.utils import timezone
from rest_framework import viewsets

from .models import Opportunity
from .serializers import OpportunitySerializer


class OpportunityViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public discovery is limited to published opportunities that have not expired.

    Create/update/approval actions must be added with explicit recruiter and IPC
    permissions in the owning workflow rather than exposing unrestricted writes.
    """

    serializer_class = OpportunitySerializer

    def get_queryset(self):
        return (
            Opportunity.objects.filter(
                status=Opportunity.Status.PUBLISHED,
                application_deadline__gt=timezone.now(),
            )
            .select_related("company")
            .order_by("-published_at", "-created_at")
        )
