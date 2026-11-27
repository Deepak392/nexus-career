from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CompanyProfileView, RecruiterOpportunityViewSet

router = DefaultRouter()
router.register(
    "opportunities",
    RecruiterOpportunityViewSet,
    basename="recruiter-opportunity",
)

urlpatterns = [
    path("company/", CompanyProfileView.as_view(), name="recruiter-company-profile"),
    path("", include(router.urls)),
]
