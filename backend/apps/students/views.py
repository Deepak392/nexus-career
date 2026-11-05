
from django.shortcuts import get_object_or_404

from rest_framework import generics, mixins, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from .models import StudentProfile
from .serializers import StudentProfileSerializer


class StudentProfileView(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    generics.GenericAPIView,
):
    serializer_class = StudentProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def check_student_role(self):
        if self.request.user.role != User.Role.STUDENT:
            raise PermissionDenied(
                "Only students can access student profiles."
            )

    def get_object(self):
        self.check_student_role()
        return get_object_or_404(
            StudentProfile,
            user=self.request.user,
        )

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.check_student_role()

        if StudentProfile.objects.filter(user=request.user).exists():
            raise ValidationError(
                {"detail": "You already have a student profile."}
            )

        return self.create(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
