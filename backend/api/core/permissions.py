"""Shared role and object permission classes for Nexus Career API."""

from rest_framework.permissions import BasePermission
from apps.accounts.models import User


class IsIPCAdmin(BasePermission):
    """Allows access only to authenticated, active IPC administrators."""

    message = "Only IPC administrators can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.IPC_ADMIN
        )


class IsSystemAdmin(BasePermission):
    """Allows access only to authenticated, active System administrators."""

    message = "Only System administrators can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.SYSTEM_ADMIN
        )


class IsIPCAdminOrSystemAdmin(BasePermission):
    """Allows access to IPC administrators or System administrators."""

    message = "Only IPC or System administrators can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role in (User.Role.IPC_ADMIN, User.Role.SYSTEM_ADMIN)
        )


class IsRecruiter(BasePermission):
    """Allows access only to authenticated, active recruiters."""

    message = "Only recruiter accounts can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.RECRUITER
        )


class IsStudent(BasePermission):
    """Allows access only to authenticated, active students."""

    message = "Only student accounts can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.STUDENT
        )


class IsAlumni(BasePermission):
    """Allows access only to authenticated, active alumni."""

    message = "Only alumni accounts can access this resource."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.role == User.Role.ALUMNI
        )
