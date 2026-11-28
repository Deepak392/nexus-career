
"""
URL configuration for Nexus Career.
"""

from django.contrib import admin
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from api.v1.health import HealthView

urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    path("health/", HealthView.as_view(), name="root-health"),

    # Nexus Career API
    path("api/v1/", include("api.v1.urls")),
    path("api-auth/", include("rest_framework.urls")),
    # API Documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="redoc",
    ),
]
