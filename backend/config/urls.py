from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


urlpatterns = [
    path("api/v1/", include("api.v1.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="redoc"),
]
