from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsStudent(BasePermission):
    message = "Only student accounts can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.STUDENT
        )
