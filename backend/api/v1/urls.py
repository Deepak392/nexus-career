from django.urls import include, path

from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.views import LogoutView, MeView, RegisterView


urlpatterns = [
    # Authentication
    path("auth/register/", RegisterView.as_view(), name="account-register"),
    path("auth/login/", TokenObtainPairView.as_view(), name="token-obtain-pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", MeView.as_view(), name="account-profile"),
    path("auth/logout/", LogoutView.as_view(), name="account-logout"),

    # Student and alumni profiles
    path("students/", include("apps.students.urls")),
    path("alumni/", include("apps.alumni.urls")),

    # Published opportunity discovery
    path("opportunities/", include("apps.opportunities.urls")),
]
