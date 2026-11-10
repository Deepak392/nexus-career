"""Shared audit logging service for administrative and workflow actions.

Implements the Delivery Plan service contract:
    audit.log(actor, action, target, context)

Also persists administrative audit records to the database (WorkflowAuditEvent)
and maintains an in-memory audit store for test assertions.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus_career.audit")

_audit_log_store: List[Dict[str, Any]] = []


def _resolve_target(target: Any) -> tuple[str, int]:
    """Resolves target instance or descriptor into (object_type, object_id)."""
    if hasattr(target, "_meta"):
        model_name = target._meta.model_name.upper()
        if model_name == "ALUMNIPROFILE":
            object_type = "AlumniProfile"
        elif model_name == "RECRUITERPROFILE":
            object_type = "RecruiterProfile"
        elif model_name == "COMPANY":
            object_type = "Company"
        elif model_name == "OPPORTUNITY":
            object_type = "Opportunity"
        elif model_name == "USER":
            object_type = "User"
        else:
            object_type = target._meta.object_name
        return object_type, int(target.pk)
    if isinstance(target, (tuple, list)) and len(target) >= 2:
        return str(target[0]), int(target[1])
    if isinstance(target, dict):
        return str(target.get("type", "UNKNOWN")), int(target.get("id", 0))
    return "UNKNOWN", 0


def log(
    actor: Any,
    action: str,
    target: Any,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Records an administrative audit event.

    Args:
        actor: The User instance performing the action.
        action: The string descriptor of the action.
        target: The target entity (model instance, tuple, or dict).
        context: Contextual metadata dictionary (sensitive values stripped).

    Returns:
        The generated audit event dictionary.
    """
    target_type, target_id = _resolve_target(target)
    safe_context = dict(context or {})

    # Sanitize any sensitive credentials
    for forbidden in ("password", "token", "refresh", "secret", "proof_bytes"):
        safe_context.pop(forbidden, None)

    event = {
        "actor_id": getattr(actor, "id", None) or getattr(actor, "pk", None),
        "actor_username": getattr(actor, "username", str(actor)),
        "actor_role": getattr(actor, "role", "UNKNOWN"),
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "details": safe_context,
    }

    _audit_log_store.append(event)
    logger.info(
        "AUDIT_EVENT: actor=%s action=%s target_type=%s target_id=%s",
        event["actor_username"],
        event["action"],
        event["target_type"],
        event["target_id"],
    )

    # Persist to database if actor is a valid User instance and models are available
    try:
        from apps.recruiters.models import WorkflowAuditEvent

        actor_user = actor if hasattr(actor, "pk") and actor.pk else None
        if actor_user and target_id:
            # Map object_type to valid choices or use upper string
            db_obj_type = target_type.upper()
            if db_obj_type in ("COMPANY", "OPPORTUNITY"):
                pass
            elif "ALUMNI" in db_obj_type:
                db_obj_type = "ALUMNI"
            elif "USER" in db_obj_type:
                db_obj_type = "USER"

            WorkflowAuditEvent.objects.create(
                actor=actor_user,
                object_type=db_obj_type,
                object_id=target_id,
                action=action,
                details=safe_context,
            )
    except Exception as exc:
        logger.warning("Could not persist WorkflowAuditEvent: %s", exc)

    return event


def log_verification_audit(
    *,
    actor: Any,
    action: str,
    target_type: str,
    target_id: Any,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compatibility interface matching S2 R1 verification audit calls."""
    return log(
        actor=actor,
        action=action,
        target=(target_type, int(target_id)),
        context=details,
    )


def get_audit_logs() -> List[Dict[str, Any]]:
    """Returns a copy of all recorded audit log events (for test assertions)."""
    return list(_audit_log_store)


def clear_audit_logs() -> None:
    """Clears the in-memory audit store between test cases."""
    _audit_log_store.clear()
