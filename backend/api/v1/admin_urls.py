from django.urls import path

from apps.alumni.views import (
    AlumniVerificationView,
    PendingAlumniVerificationView,
)
from apps.recruiters.admin_views import (
    AdminDashboardMetricsView,
    AuditLogListView,
    OpportunityApproveView,
    OpportunityRejectView,
    PendingCompanyListView,
    PendingOpportunityListView,
    RecruiterVerificationView,
    UserReactivateView,
    UserSuspendView,
)

urlpatterns = [
    # R1: Recruiter and Alumni verification
    path("recruiters/<int:id>/verify/", RecruiterVerificationView.as_view(), name="admin-recruiter-verify"),
    path("recruiters/pending/", PendingCompanyListView.as_view(), name="admin-recruiter-pending"),
    path("alumni/<int:id>/verify/", AlumniVerificationView.as_view(), name="admin-alumni-verify"),
    path("alumni/pending/", PendingAlumniVerificationView.as_view(), name="admin-alumni-pending"),

    # R2: Opportunity approval and rejection
    path("opportunities/<int:id>/approve/", OpportunityApproveView.as_view(), name="admin-opportunity-approve"),
    path("opportunities/<int:id>/reject/", OpportunityRejectView.as_view(), name="admin-opportunity-reject"),
    path("opportunities/pending/", PendingOpportunityListView.as_view(), name="admin-opportunity-pending"),

    # R3: Account suspension and reactivation
    path("users/<int:id>/suspend/", UserSuspendView.as_view(), name="admin-user-suspend"),
    path("users/<int:id>/reactivate/", UserReactivateView.as_view(), name="admin-user-reactivate"),

    # R4: Audit trail views
    path("audit-logs/", AuditLogListView.as_view(), name="admin-audit-logs"),

    # R5: Admin dashboard metrics
    path("dashboard/metrics/", AdminDashboardMetricsView.as_view(), name="admin-dashboard-metrics"),
    path("metrics/", AdminDashboardMetricsView.as_view(), name="admin-metrics"),
]
