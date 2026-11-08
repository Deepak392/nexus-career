from django.shortcuts import get_object_or_404

from rest_framework import generics, mixins, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from .models import AlumniProfile
from .serializers import AlumniProfileSerializer
from .serializers import AlumniSearchSerializer

class AlumniProfileView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):

    serializer_class = AlumniProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_alumni_role(self):
        if self.request.user.role != User.Role.ALUMNI:
            raise PermissionDenied(
                "Only alumni can access alumni profiles."
            )

    def get_object(self):
        self.check_alumni_role()
        return get_object_or_404(
            AlumniProfile,
            user=self.request.user,
        )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.check_alumni_role()

        if AlumniProfile.objects.filter(user=request.user).exists():
            raise ValidationError(
                {"detail": "You already have an alumni profile."}
            )

        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
class AlumniSearchView(generics.ListAPIView):
    serializer_class = AlumniSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = AlumniProfile.objects.filter(
            verification_status=AlumniProfile.VerificationStatus.VERIFIED
        )

        company = self.request.query_params.get("company")
        designation = self.request.query_params.get("designation")
        department = self.request.query_params.get("department")

        if company:
            queryset = queryset.filter(
                current_company__icontains=company
            )

        if designation:
            queryset = queryset.filter(
                designation__icontains=designation
            )

        if department:
            queryset = queryset.filter(
                department__icontains=department
            )

        return queryset.order_by("id")