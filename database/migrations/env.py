"""Entorno de ejecución de Alembic — async, sin URL hardcodeada.

``target_metadata`` es ``Base.metadata`` (``backend/providers/database/base_model.py``)
— vacía en este Sprint (sin tablas de negocio, ver Sprint 2.6,
"NO IMPLEMENTAR"). ``sqlalchemy.url`` se resuelve, en este orden: (1) ya
inyectada en ``config`` por quien invoque Alembic programáticamente (ver
``backend/modules/database/installer.py``, ``DatabaseInstaller``); (2) la
variable de entorno ``TEAF_DATABASE_URL`` cuando se invoca la CLI de
Alembic directamente.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from teaf._internal.providers.database.base_model import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

if not config.get_main_option("sqlalchemy.url"):
    database_url = os.environ.get("TEAF_DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)


def run_migrations_offline() -> None:
    """Genera el SQL de las migraciones sin abrir una conexión real (``--sql``)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Crea un ``AsyncEngine`` desde ``config`` y ejecuta las migraciones sobre él."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
