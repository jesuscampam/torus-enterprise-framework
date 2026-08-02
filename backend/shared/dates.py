"""Utilidades genéricas de fecha/hora. Siempre UTC — TEAF es Database Agnostic
y Cloud Ready, nunca asume la zona horaria del servidor local."""

from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Fecha/hora actual, siempre con tzinfo UTC explícito."""
    return datetime.now(UTC)


def to_iso8601(value: datetime) -> str:
    """Formatea ``value`` como string ISO 8601 (compatible con LOGGING-STANDARD.md)."""
    return value.isoformat()
