from django.urls import path

from .views import (
    AlumniEngagementMetricsView,
    AlumniGraduationProofDownloadView,
    AlumniGraduationProofUploadView,
    AlumniVerificationActionView,
    PendingAlumniVerificationView,
    AlumniProfileView,
    AlumniSearchView,
    ReferralRequestActionView,
    ReferralRequestDetailView,
    ReferralRequestListCreateView,
    ReferralResumeDownloadView,
)

urlpatterns = [
    path("profile/", AlumniProfileView.as_view(), name="alumni-profile"),
    path("graduation-proof/", AlumniGraduationProofUploadView.as_view(), name="alumni-graduation-proof-upload"),
    path("ipc/pending-verification/", PendingAlumniVerificationView.as_view(), name="ipc-pending-alumni-verification"),
    path("ipc/<int:pk>/proof/", AlumniGraduationProofDownloadView.as_view(), name="ipc-alumni-graduation-proof"),
    path("ipc/<int:pk>/<str:action>/", AlumniVerificationActionView.as_view(), name="ipc-alumni-verification-action"),
    path("search/", AlumniSearchView.as_view(), name="alumni-search"),
    path("metrics/", AlumniEngagementMetricsView.as_view(), name="alumni-metrics"),
    path(
        "referral-requests/",
        ReferralRequestListCreateView.as_view(),
        name="alumni-referral-list-create",
    ),
    path(
        "referral-requests/<int:pk>/",
        ReferralRequestDetailView.as_view(),
        name="alumni-referral-detail",
    ),
    path(
        "referral-requests/<int:pk>/resume/",
        ReferralResumeDownloadView.as_view(),
        name="alumni-referral-resume",
    ),
    path(
        "referral-requests/<int:pk>/<str:action>/",
        ReferralRequestActionView.as_view(),
        name="alumni-referral-action",
    ),
]
