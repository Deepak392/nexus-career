from django.contrib import admin

from .models import Application, ApplicationStatusHistory


class ApplicationStatusHistoryInline(admin.TabularInline):
    model = ApplicationStatusHistory
    extra = 0
    can_delete = False
    readonly_fields = ("status", "changed_by", "note", "created_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "opportunity", "status", "submitted_at")
    list_filter = ("status", "submitted_at")
    search_fields = (
        "student__username",
        "student__email",
        "opportunity__title",
        "opportunity__company__name",
    )
    readonly_fields = (
        "student",
        "opportunity",
        "resume",
        "eligibility_snapshot",
        "submitted_at",
        "updated_at",
    )
    inlines = (ApplicationStatusHistoryInline,)


@admin.register(ApplicationStatusHistory)
class ApplicationStatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("application", "status", "changed_by", "created_at")
    list_filter = ("status", "created_at")
    readonly_fields = ("application", "status", "changed_by", "note", "created_at")
