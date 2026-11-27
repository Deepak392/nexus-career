from apps.alumni.views import AlumniVerificationView
from apps.recruiters.views import RecruiterVerificationView
from django.urls import include, path
from api.v1.health import HealthView

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import (
    LogoutView,
    MeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)


urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("auth/register/", RegisterView.as_view(), name="account-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("auth/me/", MeView.as_view(), name="account-profile"),
    path("auth/logout/", LogoutView.as_view(), name="account-logout"),
    path("students/", include("apps.students.urls")),
    path("applications/", include("apps.applications.urls")),
    path("notifications/", include("apps.notifications.urls")),
    path("alumni/", include("apps.alumni.urls")),
    path("opportunities/", include("apps.opportunities.urls")),
    path("recruiters/", include("apps.recruiters.urls")),
    path("ipc/", include("apps.recruiters.ipc_urls")),

    path(
        "admin/recruiters/<int:id>/verify/",
        RecruiterVerificationView.as_view(),
        name="admin-recruiter-verify",
    ),
    path(
        "admin/alumni/<int:id>/verify/",
        AlumniVerificationView.as_view(),
        name="admin-alumni-verify",
    ),
]