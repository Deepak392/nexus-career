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

    # Student & Alumni routes (Nayana)
    path("students/", include("apps.students.urls")),
    path("alumni/", include("apps.alumni.urls")),
]
