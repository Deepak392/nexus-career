from .models import Notification


def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message,
    deduplication_key,
    application=None,
    referral_request=None,
):
    notification, created = Notification.objects.get_or_create(
        deduplication_key=deduplication_key,
        defaults={
            "recipient": recipient,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "application": application,
            "referral_request": referral_request,
        },
    )

    return notification, created