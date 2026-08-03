"""``Base`` declarativa y ``AuditMixin`` — infraestructura de modelado, sin tablas de negocio.

Ninguna aplicación construida sobre TEAF debería declarar sus modelos sin
heredar de ``Base``+``AuditMixin`` — es lo que garantiza las columnas de
auditoría obligatorias de [DATABASE-STANDARD.md](../../../docs/standards/DATABASE-STANDARD.md),
sección 3-4 (UUID como clave primaria, ``created_at``/``updated_at``/``deleted_at``)
en cada tabla, sin repetir su declaración. Sin ninguna entidad concreta
definida aquí (ver Sprint 2.6, "NO IMPLEMENTAR": sin tablas de negocio).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Uuid


class Base(DeclarativeBase):
    """Base declarativa compartida por todos los modelos SQLAlchemy de TEAF."""


class AuditMixin:
    """Columnas de auditoría obligatorias en toda tabla de negocio.

    ``Uuid`` (tipo genérico de SQLAlchemy 2.x) se traduce al tipo nativo de
    cada dialecto (``UUID`` en PostgreSQL, ``CHAR(32)`` en SQLite) — Database
    Agnostic sin encoding manual.
    """

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    #: ``NULL`` = registro activo (baja lógica, nunca ``DELETE`` físico).
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
