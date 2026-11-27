"""Central application status transition service for Nexus Career.

Implements the Delivery Plan service contract (page 13):
    transition_application_status(application, new_status, actor, note="")
Owner: Sreehari (Eligibility & Applications)
Used by: Recruiter API (Charan Tej), Admin (Anji)
"""

from typing import Optional
from django.core.exceptions import ValidationError
from django.db import transaction

from api.core import audit, events
from apps.applications.models import Application, ApplicationStatusHistory

ALLOWED_TRANSITIONS = {
    Application.Status.SUBMITTED: {
        Application.Status.UNDER_REVIEW,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.UNDER_REVIEW: {
        Application.Status.SHORTLISTED,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.SHORTLISTED: {
        Application.Status.SELECTED,
        Application.Status.REJECTED,
        Application.Status.WITHDRAWN,
    },
    Application.Status.SELECTED: set(),
    Application.Status.REJECTED: set(),
    Application.Status.WITHDRAWN: set(),
}


@transaction.atomic
def transition_application_status(
    application: Application,
    new_status: str,
    actor,
    note: str = "",
) -> Application:
    """Transitions an application status through permitted lifecycle states.

    Enforces allowed state transitions, records audit events, creates status history,
    and dispatches in-app notification to the student.
    """
    if new_status not in Application.Status.values:
        raise ValidationError(f"Invalid application status: '{new_status}'.")

    current_status = application.status
    if current_status == new_status:
        return application

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValidationError(
            f"Cannot transition application from '{current_status}' to '{new_status}'."
        )

    # Update application
    application.status = new_status
    application.save(update_fields=["status", "updated_at"])

    # Record history
    ApplicationStatusHistory.objects.create(
        application=application,
        status=new_status,
        changed_by=actor,
        note=note or f"Status changed to {new_status} by {actor.username}.",
    )

    # Shared audit log
    audit.log(
        actor=actor,
        action="APPLICATION_STATUS_CHANGED",
        target=f"APPLICATION:{application.id}",
        context={
            "application_id": application.id,
            "opportunity_id": application.opportunity_id,
            "opportunity_title": application.opportunity.title,
            "from_status": current_status,
            "to_status": new_status,
            "note": note,
        },
    )

    # In-app event & notification to student
    events.emit(
        "APPLICATION_STATUS_CHANGED",
        {
            "recipient_id": application.student_id,
            "opportunity_id": application.opportunity_id,
            "opportunity_title": application.opportunity.title,
            "new_status": new_status,
            "title": "Application Status Updated",
            "message": f"Your application for '{application.opportunity.title}' has been moved to {new_status}.",
        },
    )

    return application
