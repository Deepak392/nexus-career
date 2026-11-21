from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Liveness check: confirms the app is running. No login, no database."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Service health check",
        description="Public liveness check confirming the backend is up. Requires no authentication.",
        responses={
            200: inline_serializer(
                name="HealthCheckResponse",
                fields={"status": serializers.CharField(default="ok")},
            )
        },
    )
    def get(self, request):
        return Response({"status": "ok"})