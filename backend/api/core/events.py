"""Shared event dispatching boundary for Nexus Career.

Implements the Delivery Plan service contract:
    events.emit(event_type, payload)

Ensures that notification/event dispatch failure never breaks the primary transaction.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus_career.events")

_event_store: List[Dict[str, Any]] = []


def emit(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Emits an event asynchronously / decoupled from the primary database action.

    Args:
        event_type: Event type identifier (e.g. 'OPPORTUNITY_APPROVED', 'OPPORTUNITY_REJECTED').
        payload: Event data payload containing entity and recipient information.

    Returns:
        The recorded event record.
    """
    event = {
        "event_type": event_type,
        "payload": payload,
    }
    _event_store.append(event)
    logger.info("EVENT_EMITTED: type=%s payload=%s", event_type, payload)

    # Deliver in-app notification if recipient is identified
    try:
        from apps.accounts.models import User
        from apps.notifications.models import Notification

        recipient_id = payload.get("recipient_id")
        recipient = None
        if recipient_id:
            recipient = User.objects.filter(id=recipient_id).first()

        if recipient:
            title = payload.get("title", f"Update: {event_type}")
            message = payload.get("message", "")
            if not message:
                opp_title = payload.get("opportunity_title", "your opportunity")
                if event_type == "OPPORTUNITY_APPROVED":
                    title = "Opportunity Approved"
                    message = f"Your opportunity '{opp_title}' was approved and published."
                elif event_type == "OPPORTUNITY_REJECTED":
                    title = "Opportunity Rejected"
                    reason = payload.get("reason", "")
                    message = f"Your opportunity '{opp_title}' was rejected. Reason: {reason}"

            # Create notification record
            Notification.objects.create(
                recipient=recipient,
                notification_type=event_type[:40],
                title=title[:160],
                message=message[:500],
            )
    except Exception as exc:
        # Per Delivery Plan: a notification failure never breaks the main action
        logger.warning("Could not persist in-app notification for event %s: %s", event_type, exc)

    return event


def get_emitted_events() -> List[Dict[str, Any]]:
    """Returns all emitted events for test assertions."""
    return list(_event_store)


def clear_emitted_events() -> None:
    """Clears the in-memory event store between tests."""
    _event_store.clear()
