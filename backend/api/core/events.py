import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

_handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = defaultdict(list)


def register_handler(
    event_type: str,
    handler: Callable[[dict[str, Any]], None],
) -> None:
    """Register a handler for an event type."""
    if handler not in _handlers[event_type]:
        _handlers[event_type].append(handler)


def emit(event_type: str, payload: dict[str, Any]) -> None:
    """Dispatch an event without allowing handler failures to break the main action."""
    for handler in _handlers[event_type]:
        try:
            handler(payload)
        except Exception:
            logger.exception(
                "Event handler failed for event type '%s'",
                event_type,
            )