"""Utilidades genéricas para identificadores (UUID). Sin lógica de negocio."""

from __future__ import annotations

import uuid


def new_uuid() -> str:
    """Genera un UUID4 como string — usado, por ejemplo, para correlation-ids nuevos."""
    return str(uuid.uuid4())
