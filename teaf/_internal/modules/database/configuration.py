"""``DatabaseConfiguration`` — selección de proveedor y parámetros de conexión.

"Toda selección deberá ser configurable" (Sprint 2.6, ítem 7): el dialecto
(SQLite/PostgreSQL/SQL Server) y todos los parámetros de conexión se
resuelven desde un ``Mapping`` (``from_mapping``) — típicamente
``ModuleContext.configuration``, poblado por quien construya el contexto a
partir de ``backend/config/Settings`` (ver DATABASE-STANDARD.md, sección 8:
"la configuración del pool... se resuelve vía backend/config/"). Este
módulo no importa ``backend/config/`` directamente — mantiene la misma
independencia que el resto de ``backend/sdk/``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from teaf._internal.providers.database.engine import ConnectionParameters, DatabaseDialect

#: Ruta por defecto de las migraciones Alembic (ver database/migrations/).
DEFAULT_MIGRATIONS_PATH = "database/migrations"


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    return int(str(value))


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _coerce_optional_str(value: object) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True, slots=True)
class DatabaseConfiguration:
    """Configuración completa del Database Module."""

    dialect: DatabaseDialect = DatabaseDialect.SQLITE
    database: str = ":memory:"
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False
    migrations_path: str = DEFAULT_MIGRATIONS_PATH

    @property
    def connection_parameters(self) -> ConnectionParameters:
        """Traduce esta configuración a los parámetros de ``providers/database/engine.py``."""
        return ConnectionParameters(
            database=self.database,
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> DatabaseConfiguration:
        """Construye la configuración desde un ``Mapping`` (claves ausentes usan el default)."""
        dialect_value = values.get("dialect", DatabaseDialect.SQLITE)
        dialect = (
            dialect_value
            if isinstance(dialect_value, DatabaseDialect)
            else DatabaseDialect(str(dialect_value))
        )
        port_value = values.get("port")
        return cls(
            dialect=dialect,
            database=str(values.get("database", ":memory:")),
            host=_coerce_optional_str(values.get("host")),
            port=_coerce_int(port_value, 0) if port_value is not None else None,
            username=_coerce_optional_str(values.get("username")),
            password=_coerce_optional_str(values.get("password")),
            pool_size=_coerce_int(values.get("pool_size"), 5),
            max_overflow=_coerce_int(values.get("max_overflow"), 10),
            echo=_coerce_bool(values.get("echo"), False),
            migrations_path=str(values.get("migrations_path", DEFAULT_MIGRATIONS_PATH)),
        )
