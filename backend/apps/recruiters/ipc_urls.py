from django.urls import path

from .admin_views import (
    CompanyRejectView,
    CompanyVerifyView,
    OpportunityApproveView,
    OpportunityRejectView,
    PendingCompanyListView,
    PendingOpportunityListView,
)

urlpatterns = [
    path("companies/pending/", PendingCompanyListView.as_view(), name="ipc-pending-companies"),
    path("companies/<int:pk>/verify/", CompanyVerifyView.as_view(), name="ipc-company-verify"),
    path("companies/<int:pk>/reject/", CompanyRejectView.as_view(), name="ipc-company-reject"),
    path("opportunities/pending/", PendingOpportunityListView.as_view(), name="ipc-pending-opportunities"),
    path("opportunities/<int:pk>/approve/", OpportunityApproveView.as_view(), name="ipc-opportunity-approve"),
    path("opportunities/<int:pk>/reject/", OpportunityRejectView.as_view(), name="ipc-opportunity-reject"),
]
