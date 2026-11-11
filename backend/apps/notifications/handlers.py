from apps.applications.models import Application
from apps.notifications.models import Notification
from apps.notifications.services import create_notification
from apps.opportunities.models import Opportunity
from apps.alumni.models import ReferralRequest
from django.contrib.auth import get_user_model

def handle_application_submitted(payload):
    application = Application.objects.select_related(
        "student",
        "opportunity",
        "opportunity__company",
    ).get(pk=payload["application_id"])

    create_notification(
        recipient=application.student,
        notification_type=Notification.NotificationType.APPLICATION_SUBMITTED,
        title="Application submitted",
        message=(
            f"Your application for {application.opportunity.title} at "
            f"{application.opportunity.company.name} was submitted successfully."
        ),
        application=application,
        deduplication_key=f"application:{application.pk}:submitted",
    )
    
def handle_referral_requested(payload):
    referral = ReferralRequest.objects.select_related(
        "student",
        "alumni_profile__user",
    ).get(pk=payload["referral_request_id"])

    create_notification(
        recipient=referral.alumni_profile.user,
        notification_type=Notification.NotificationType.REFERRAL_REQUEST,
        title="New student referral request",
        message=(
            f"{referral.student.get_full_name() or referral.student.username} "
            "has requested a referral."
        ),
        referral_request=referral,
        deduplication_key=payload["deduplication_key"],
    )
    
def handle_referral_updated(payload):
    User = get_user_model()

    referral = ReferralRequest.objects.get(
        pk=payload["referral_request_id"]
    )
    recipient = User.objects.get(pk=payload["recipient_id"])

    create_notification(
        recipient=recipient,
        notification_type=payload["notification_type"],
        title=payload["title"],
        message=payload["message"],
        referral_request=referral,
        deduplication_key=payload["deduplication_key"],
    )
    
def handle_opportunity_approved(payload):
    opportunity = Opportunity.objects.get(
        pk=payload["opportunity_id"]
    )

    create_notification(
        recipient=opportunity.created_by,
        notification_type=Notification.NotificationType.OPPORTUNITY_APPROVED,
        title="Opportunity approved",
        message=f"Your opportunity '{opportunity.title}' has been approved and published.",
        deduplication_key=payload["deduplication_key"],
    )


def handle_opportunity_rejected(payload):
    opportunity = Opportunity.objects.get(
        pk=payload["opportunity_id"]
    )

    create_notification(
        recipient=opportunity.created_by,
        notification_type=Notification.NotificationType.OPPORTUNITY_REJECTED,
        title="Opportunity rejected",
        message=(
            f"Your opportunity '{opportunity.title}' was rejected. "
            f"Reason: {opportunity.rejection_reason}"
        ),
        deduplication_key=payload["deduplication_key"],
    )