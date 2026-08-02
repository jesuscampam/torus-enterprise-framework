"""``EventBus`` — publicación/suscripción síncrona interna del Framework.

Exclusivamente en proceso: no hay cola, no hay broker, no hay entrega
garantizada entre instancias (eso sería mensajería distribuida, fuera de
alcance de este Sprint). Sirve para desacoplar piezas del Runtime entre sí
(por ejemplo, ``Runtime`` publica eventos de ciclo de vida que cualquier
suscriptor futuro puede escuchar sin que ``Runtime`` conozca quién escucha).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

EventHandler = Callable[["Event"], None]


@dataclass(frozen=True, slots=True)
class Event:
    """Evento interno del Framework: un nombre y un payload de solo lectura."""

    name: str
    payload: Mapping[str, object] = field(default_factory=dict)


class EventBus:
    """Registro de suscriptores por nombre de evento y despacho síncrono."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = {}

    def subscribe(self, event_name: str, handler: EventHandler) -> None:
        """Registra ``handler`` para ejecutarse en cada ``publish()`` de ``event_name``."""
        self._subscribers.setdefault(event_name, []).append(handler)

    def unsubscribe(self, event_name: str, handler: EventHandler) -> None:
        """Elimina ``handler`` de los suscriptores de ``event_name``, si estaba registrado."""
        handlers = self._subscribers.get(event_name)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def publish(self, event: Event) -> None:
        """Invoca, en orden de suscripción, a todos los handlers de ``event.name``."""
        for handler in tuple(self._subscribers.get(event.name, ())):
            handler(event)

    def subscriber_count(self, event_name: str) -> int:
        """Número de suscriptores actuales de ``event_name`` (útil para tests/depuración)."""
        return len(self._subscribers.get(event_name, ()))
