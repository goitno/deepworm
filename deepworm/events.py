"""Progress events for the research pipeline.

Provides a structured event system that allows consumers to track
research progress for building custom UIs, logging, or integrations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class EventType(Enum):
    """Research event types."""
    RESEARCH_START = "research_start"
    ITERATION_START = "iteration_start"
    ITERATION_END = "iteration_end"
    QUERIES_GENERATED = "queries_generated"
    SEARCH_START = "search_start"
    SEARCH_COMPLETE = "search_complete"
    FETCH_START = "fetch_start"
    FETCH_COMPLETE = "fetch_complete"
    ANALYSIS_START = "analysis_start"
    ANALYSIS_COMPLETE = "analysis_complete"
    SYNTHESIS_START = "synthesis_start"
    SYNTHESIS_COMPLETE = "synthesis_complete"
    RESEARCH_COMPLETE = "research_complete"
    ERROR = "error"


@dataclass
class Event:
    """A research progress event."""
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventEmitter:
    """Simple event emitter for research progress tracking.

    Usage:
        emitter = EventEmitter()
        emitter.on(EventType.ITERATION_START, lambda e: print(e.message))
        emitter.on_all(lambda e: log(e))
    """

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = {}
        self._global_handlers: list[EventHandler] = []

    def on(self, event_type: EventType, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def on_all(self, handler: EventHandler) -> None:
        """Register a handler that receives all events."""
        self._global_handlers.append(handler)

    def emit(self, event: Event) -> None:
        """Emit an event to all registered handlers."""
        # Call specific handlers
        for handler in self._handlers.get(event.type, []):
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors break research

        # Call global handlers
        for handler in self._global_handlers:
            try:
                handler(event)
            except Exception:
                pass

    def off(self, event_type: EventType, handler: Optional[EventHandler] = None) -> None:
        """Remove a handler. If handler is None, remove all for that type."""
        if handler is None:
            self._handlers.pop(event_type, None)
        elif event_type in self._handlers:
            self._handlers[event_type] = [
                h for h in self._handlers[event_type] if h is not handler
            ]

    def clear(self) -> None:
        """Remove all handlers."""
        self._handlers.clear()
        self._global_handlers.clear()
