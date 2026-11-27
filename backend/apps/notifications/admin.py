from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "title", "created_at", "read_at")
    list_filter = ("notification_type", "created_at", "read_at")
    search_fields = ("recipient__username", "recipient__email", "title", "message")
    readonly_fields = (
        "recipient",
        "notification_type",
        "title",
        "message",
        "application",
        "created_at",
        "read_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
