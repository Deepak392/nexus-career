from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
    )
    list_filter = ("role", "is_verified", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Nexus Career access",
            {"fields": ("role", "is_verified")},
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Nexus Career access",
            {"fields": ("email", "role", "is_verified")},
        ),
    )
