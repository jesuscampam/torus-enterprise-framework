"""Utilidades genéricas de validación. Validaciones de forma, no de negocio."""

from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(value: str) -> bool:
    """Validación sintáctica simple de email (no verifica existencia del dominio)."""
    return bool(_EMAIL_RE.match(value))


def is_not_empty(value: str | None) -> bool:
    """``True`` si ``value`` tiene contenido no vacío tras eliminar espacios."""
    return value is not None and value.strip() != ""
