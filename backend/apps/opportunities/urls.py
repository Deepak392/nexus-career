from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import OpportunityEligibilityView, OpportunityViewSet

router = DefaultRouter()
router.register(r"", OpportunityViewSet, basename="opportunity")

urlpatterns = [
    path("<int:pk>/eligibility/", OpportunityEligibilityView.as_view(), name="opportunity-eligibility"),
    path("", include(router.urls)),
]
