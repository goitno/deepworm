"""Tests for deepworm.events."""

from deepworm.events import Event, EventEmitter, EventType


def test_emit_and_handle():
    """Should call handler when event is emitted."""
    received = []
    emitter = EventEmitter()
    emitter.on(EventType.RESEARCH_START, lambda e: received.append(e))
    emitter.emit(Event(type=EventType.RESEARCH_START, message="hello"))
    assert len(received) == 1
    assert received[0].message == "hello"


def test_global_handler():
    """on_all handler should receive all events."""
    received = []
    emitter = EventEmitter()
    emitter.on_all(lambda e: received.append(e.type))
    emitter.emit(Event(type=EventType.RESEARCH_START))
    emitter.emit(Event(type=EventType.ITERATION_START))
    emitter.emit(Event(type=EventType.RESEARCH_COMPLETE))
    assert len(received) == 3


def test_off_specific_handler():
    """Should remove a specific handler."""
    received = []
    handler = lambda e: received.append(e)
    emitter = EventEmitter()
    emitter.on(EventType.RESEARCH_START, handler)
    emitter.off(EventType.RESEARCH_START, handler)
    emitter.emit(Event(type=EventType.RESEARCH_START))
    assert len(received) == 0


def test_off_all_handlers():
    """Should remove all handlers for a type."""
    received = []
    emitter = EventEmitter()
    emitter.on(EventType.RESEARCH_START, lambda e: received.append(1))
    emitter.on(EventType.RESEARCH_START, lambda e: received.append(2))
    emitter.off(EventType.RESEARCH_START)
    emitter.emit(Event(type=EventType.RESEARCH_START))
    assert len(received) == 0


def test_clear():
    """Should remove all handlers."""
    received = []
    emitter = EventEmitter()
    emitter.on(EventType.RESEARCH_START, lambda e: received.append(1))
    emitter.on_all(lambda e: received.append(2))
    emitter.clear()
    emitter.emit(Event(type=EventType.RESEARCH_START))
    assert len(received) == 0


def test_handler_error_does_not_break():
    """Handler errors should not prevent other handlers from running."""
    received = []
    emitter = EventEmitter()
    emitter.on(EventType.RESEARCH_START, lambda e: 1 / 0)  # raises
    emitter.on(EventType.RESEARCH_START, lambda e: received.append("ok"))
    emitter.emit(Event(type=EventType.RESEARCH_START))
    assert received == ["ok"]


def test_event_data():
    """Event should carry data dict."""
    event = Event(
        type=EventType.QUERIES_GENERATED,
        data={"queries": ["q1", "q2"], "count": 2},
        message="Generated 2 queries",
    )
    assert event.data["count"] == 2
    assert len(event.data["queries"]) == 2
