from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness check: confirms the app is running. No login, no database."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Health check",
        description="Liveness check: confirms the app is running. No login, no database.",
        responses={200: OpenApiResponse(description="Service is healthy")},
    )
    def get(self, request):
        return Response({"status": "ok"})
