from django.urls import include, path

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.accounts.views import (
    RegisterView,
    MeView,
    LogoutView,
)
from apps.alumni.views import AlumniVerificationView
from apps.recruiters.views import RecruiterVerificationView


urlpatterns = [
    # Authentication routes (Deepak)
    path(
        "auth/register/",
        RegisterView.as_view(),
        name="account-register",
    ),
    path(
        "auth/login/",
        TokenObtainPairView.as_view(),
        name="token-obtain-pair",
    ),
    path(
        "auth/refresh/",
        TokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path(
        "auth/me/",
        MeView.as_view(),
        name="account-profile",
    ),
    path(
        "auth/logout/",
        LogoutView.as_view(),
        name="account-logout",
    ),

    # IPC Administration & Verification routes (Anji S2 R1)
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

    # Student & Alumni profile routes (Nayana)
    path("students/", include("apps.students.urls")),
    path("alumni/", include("apps.alumni.urls")),
]
