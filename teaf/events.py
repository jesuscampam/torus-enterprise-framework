"""``teaf.events`` — publicación/suscripción interna del framework.

Fachada sobre ``backend/runtime/event_bus.py`` (Sprint 2.3). ``Event`` se
reexporta junto a ``EventBus`` porque ``EventBus.publish()`` lo exige como
argumento — sin él no hay forma de publicar un evento usando solo símbolos
públicos.
"""

from __future__ import annotations

from backend.runtime.event_bus import Event, EventBus

__all__ = ["Event", "EventBus"]
