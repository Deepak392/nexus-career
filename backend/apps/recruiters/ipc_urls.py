from django.urls import path

from .admin_views import (
    AuditLogListView,
    CompanyRejectView,
    CompanyVerifyView,
    OpportunityApproveView,
    OpportunityRejectView,
    PendingCompanyListView,
    PendingOpportunityListView,
    UserReactivateView,
    UserSuspendView,
)

urlpatterns = [
    path("companies/pending/", PendingCompanyListView.as_view(), name="ipc-pending-companies"),
    path("companies/<int:pk>/verify/", CompanyVerifyView.as_view(), name="ipc-company-verify"),
    path("companies/<int:pk>/reject/", CompanyRejectView.as_view(), name="ipc-company-reject"),
    path("opportunities/pending/", PendingOpportunityListView.as_view(), name="ipc-pending-opportunities"),
    path("opportunities/<int:pk>/approve/", OpportunityApproveView.as_view(), name="ipc-opportunity-approve"),
    path("opportunities/<int:pk>/reject/", OpportunityRejectView.as_view(), name="ipc-opportunity-reject"),
    path("users/<int:pk>/suspend/", UserSuspendView.as_view(), name="ipc-user-suspend"),
    path("users/<int:pk>/reactivate/", UserReactivateView.as_view(), name="ipc-user-reactivate"),
    path("audit-logs/", AuditLogListView.as_view(), name="ipc-audit-logs"),
]
