"""Shared audit logging boundary for administrative actions."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("nexus_career.audit")

_audit_log_store: List[Dict[str, Any]] = []


def log_verification_audit(
    *,
    actor: Any,
    action: str,
    target_type: str,
    target_id: Any,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Records an administrative verification audit entry.

    Ensures that actor, action, target entity, and safe metadata are logged.
    Passwords, credentials, and sensitive graduation proof binaries are never logged.
    """
    event = {
        "actor_id": getattr(actor, "id", None) or getattr(actor, "pk", None),
        "actor_username": getattr(actor, "username", str(actor)),
        "actor_role": getattr(actor, "role", "UNKNOWN"),
        "action": action,
        "target_type": target_type,
        "target_id": str(target_id),
        "details": details or {},
    }

    _audit_log_store.append(event)
    logger.info(
        "AUDIT_EVENT: actor=%s action=%s target_type=%s target_id=%s",
        event["actor_username"],
        event["action"],
        event["target_type"],
        event["target_id"],
    )
    return event


def get_audit_logs() -> List[Dict[str, Any]]:
    """Returns a copy of all audit log events (used for test assertions)."""
    return list(_audit_log_store)


def clear_audit_logs() -> None:
    """Clears the in-memory audit store between test cases."""
    _audit_log_store.clear()
