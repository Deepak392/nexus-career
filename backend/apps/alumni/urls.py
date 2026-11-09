from django.urls import path

from .views import (
    AlumniEngagementMetricsView,
    AlumniProfileView,
    AlumniSearchView,
    ReferralRequestActionView,
    ReferralRequestDetailView,
    ReferralRequestListCreateView,
    ReferralResumeDownloadView,
)

urlpatterns = [
    path("profile/", AlumniProfileView.as_view(), name="alumni-profile"),
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
