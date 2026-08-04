"""``DatabaseDialect`` y construcción del motor SQLAlchemy 2.x asíncrono.

Único punto del framework que conoce las cadenas de conexión concretas y
los drivers asíncronos por dialecto — el resto de ``backend/providers/database/``
solo conoce un ``AsyncEngine`` ya construido. Soporta SQLite (desarrollo,
``aiosqlite``) y PostgreSQL (``asyncpg``) con conexión real; SQL Server
tiene la estructura preparada (dialecto, construcción de URL) pero sin
driver instalado — ``create_engine`` fallaría al intentar conectar hasta
que un Sprint futuro añada ``aioodbc`` como dependencia real. Sin Oracle
(ver Sprint 2.6, "NO IMPLEMENTAR").

Deliberadamente **no importa** ``backend/modules/database/`` (donde vive
``DatabaseConfiguration``) — recibe parámetros primitivos
(``ConnectionParameters``) para no invertir la dirección de dependencias:
``modules/`` depende de ``providers/``, nunca al revés.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool


class DatabaseDialect(str, Enum):
    """Motores de base de datos soportados por el proveedor SQLAlchemy."""

    #: Desarrollo local / tests — sin servidor externo.
    SQLITE = "sqlite"
    #: Motor oficial de TEAF (ver docs/architecture/STACK.md).
    POSTGRESQL = "postgresql"
    #: Estructura preparada — sin driver instalado todavía (ver docstring del módulo).
    SQLSERVER = "sqlserver"


@dataclass(frozen=True, slots=True)
class ConnectionParameters:
    """Parámetros de conexión, independientes del dialecto.

    ``host``/``port``/``username``/``password`` se ignoran para SQLite,
    donde ``database`` es la ruta del archivo (o ``":memory:"``/``""``
    para una base de datos en memoria).
    """

    database: str
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None


_DRIVER_BY_DIALECT: dict[DatabaseDialect, str] = {
    DatabaseDialect.SQLITE: "sqlite+aiosqlite",
    DatabaseDialect.POSTGRESQL: "postgresql+asyncpg",
    DatabaseDialect.SQLSERVER: "mssql+aioodbc",
}


def is_in_memory_sqlite(params: ConnectionParameters) -> bool:
    """``True`` si ``params.database`` describe una base de datos SQLite en memoria."""
    return params.database in ("", ":memory:")


def build_database_url(dialect: DatabaseDialect, params: ConnectionParameters) -> str:
    """Construye la URL de conexión SQLAlchemy para ``dialect`` a partir de ``params``."""
    driver = _DRIVER_BY_DIALECT[dialect]
    if dialect is DatabaseDialect.SQLITE:
        return f"{driver}:///{params.database}"

    credentials = ""
    if params.username:
        credentials = params.username
        if params.password:
            credentials += f":{params.password}"
        credentials += "@"
    host = params.host or "localhost"
    port = f":{params.port}" if params.port else ""
    return f"{driver}://{credentials}{host}{port}/{params.database}"


def create_engine(
    dialect: DatabaseDialect,
    params: ConnectionParameters,
    *,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> AsyncEngine:
    """Construye un ``AsyncEngine`` para ``dialect``/``params``.

    Una base de datos SQLite en memoria usa ``StaticPool`` — sin eso, cada
    conexión del pool vería una base de datos distinta y vacía, ya que
    SQLite en memoria no persiste fuera de la conexión que la creó.
    """
    url = build_database_url(dialect, params)
    if dialect is DatabaseDialect.SQLITE:
        if is_in_memory_sqlite(params):
            return create_async_engine(
                url,
                echo=echo,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False},
            )
        return create_async_engine(url, echo=echo)
    return create_async_engine(url, echo=echo, pool_size=pool_size, max_overflow=max_overflow)
