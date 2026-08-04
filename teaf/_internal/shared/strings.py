"""Utilidades genéricas de manipulación de strings. Sin lógica de negocio."""

from __future__ import annotations

import re

_SNAKE_CASE_RE = re.compile(r"(?<!^)(?=[A-Z])")


def is_blank(value: str | None) -> bool:
    """``True`` si ``value`` es ``None``, vacío o solo espacios en blanco."""
    return value is None or value.strip() == ""


def to_snake_case(value: str) -> str:
    """Convierte ``camelCase``/``PascalCase`` a ``snake_case``."""
    return _SNAKE_CASE_RE.sub("_", value).lower()


def truncate(value: str, max_length: int, *, suffix: str = "...") -> str:
    """Trunca ``value`` a ``max_length`` caracteres, añadiendo ``suffix`` si se recorta."""
    if max_length <= 0:
        raise ValueError("max_length debe ser mayor que 0")
    if len(value) <= max_length:
        return value
    return value[: max(0, max_length - len(suffix))] + suffix
