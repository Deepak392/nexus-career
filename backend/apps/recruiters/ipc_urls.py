from django.urls import path

from apps.alumni.ipc_views import (
    AlumniRejectView,
    AlumniVerifyView,
    PendingAlumniListView,
)

from .admin_views import (
    CompanyRejectView,
    CompanyVerifyView,
    OpportunityApproveView,
    OpportunityRejectView,
    PendingCompanyListView,
    PendingOpportunityListView,
)

urlpatterns = [
    path("alumni/pending/", PendingAlumniListView.as_view(), name="ipc-pending-alumni"),
    path("alumni/<int:pk>/verify/", AlumniVerifyView.as_view(), name="ipc-alumni-verify"),
    path("alumni/<int:pk>/reject/", AlumniRejectView.as_view(), name="ipc-alumni-reject"),
    path("companies/pending/", PendingCompanyListView.as_view(), name="ipc-pending-companies"),
    path("companies/<int:pk>/verify/", CompanyVerifyView.as_view(), name="ipc-company-verify"),
    path("companies/<int:pk>/reject/", CompanyRejectView.as_view(), name="ipc-company-reject"),
    path("opportunities/pending/", PendingOpportunityListView.as_view(), name="ipc-pending-opportunities"),
    path("opportunities/<int:pk>/approve/", OpportunityApproveView.as_view(), name="ipc-opportunity-approve"),
    path("opportunities/<int:pk>/reject/", OpportunityRejectView.as_view(), name="ipc-opportunity-reject"),
]
