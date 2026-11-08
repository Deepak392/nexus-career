from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsRecruiter(BasePermission):
    message = "Only recruiter accounts can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.RECRUITER
        )


class IsIPCAdmin(BasePermission):
    message = "Only IPC administrators can perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == User.Role.IPC_ADMIN
        )
