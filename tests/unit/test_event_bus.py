"""Pruebas unitarias de backend/runtime/event_bus.py (EventBus)."""

from __future__ import annotations

from backend.runtime.event_bus import Event, EventBus


def test_publish_without_subscribers_does_nothing() -> None:
    bus = EventBus()
    bus.publish(Event(name="framework.started"))  # no debe lanzar


def test_subscriber_receives_published_event() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("framework.started", received.append)

    event = Event(name="framework.started", payload={"foo": "bar"})
    bus.publish(event)

    assert received == [event]


def test_multiple_subscribers_are_all_notified_in_order() -> None:
    bus = EventBus()
    order: list[str] = []
    bus.subscribe("evt", lambda _e: order.append("first"))
    bus.subscribe("evt", lambda _e: order.append("second"))

    bus.publish(Event(name="evt"))

    assert order == ["first", "second"]


def test_subscribers_of_other_events_are_not_notified() -> None:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("evt.a", received.append)

    bus.publish(Event(name="evt.b"))

    assert received == []


def test_unsubscribe_stops_future_notifications() -> None:
    bus = EventBus()
    received: list[Event] = []

    def handler(event: Event) -> None:
        received.append(event)

    bus.subscribe("evt", handler)
    bus.unsubscribe("evt", handler)
    bus.publish(Event(name="evt"))

    assert received == []


def test_unsubscribe_unknown_handler_does_not_raise() -> None:
    bus = EventBus()
    bus.unsubscribe("evt", lambda _e: None)  # no debe lanzar


def test_subscriber_count_reflects_subscriptions() -> None:
    bus = EventBus()
    assert bus.subscriber_count("evt") == 0

    bus.subscribe("evt", lambda _e: None)
    bus.subscribe("evt", lambda _e: None)

    assert bus.subscriber_count("evt") == 2
