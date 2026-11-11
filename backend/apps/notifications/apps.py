from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"

    def ready(self):
        from api.core.events import register_handler
        from apps.notifications.handlers import handle_application_submitted
        from apps.notifications.handlers import handle_referral_requested
        from apps.notifications.handlers import handle_referral_updated
        from apps.notifications.handlers import handle_opportunity_approved
        from apps.notifications.handlers import handle_opportunity_rejected
        
        register_handler(
            "application.submitted",
            handle_application_submitted,
        )
        register_handler(
            "referral.requested",
            handle_referral_requested,
        )
        register_handler(
            "referral.updated",
            handle_referral_updated,
        )
        register_handler(
            "opportunity.approved",
            handle_opportunity_approved,
        )

        register_handler(
            "opportunity.rejected",
            handle_opportunity_rejected,
        )