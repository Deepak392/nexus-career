"""Shared permission classes for Nexus Career API."""

from rest_framework.permissions import BasePermission

from apps.accounts.models import User


class IsIPCAdmin(BasePermission):
    """Allows access only to authenticated active users with the IPC_ADMIN role."""

    message = "Only IPC administrators are permitted to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and getattr(request.user, "role", None) == User.Role.IPC_ADMIN
        )


class IsSystemAdmin(BasePermission):
    """Allows access only to authenticated active users with the SYSTEM_ADMIN role."""

    message = "Only system administrators are permitted to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and getattr(request.user, "role", None) == User.Role.SYSTEM_ADMIN
        )
