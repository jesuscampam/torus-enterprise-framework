"""``DatabaseInstaller`` — ejecuta migraciones Alembic mediante su API programática.

Deliberadamente síncrono: la API de comandos de Alembic (``command.upgrade``)
gestiona su propio bucle de eventos internamente (ver
``database/migrations/env.py``, ``asyncio.run(...)``) — invocarlo desde
dentro de un ``Runtime`` ya en ejecución (con su propio bucle ``asyncio``
activo) fallaría con "cannot run event loop while another loop is
running". Por eso ``DatabaseModule`` **nunca** llama a este instalador
desde sus hooks async: aplicar migraciones es un paso de despliegue
explícito y separado (ver docs/modules/database/MIGRATIONS.md), no parte
del arranque del Runtime.

Solo infraestructura: ninguna migración de negocio se genera ni se aplica
aquí (ver Sprint 2.6, "NO IMPLEMENTAR").
"""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory


class DatabaseInstaller:
    """Orquesta Alembic (upgrade/downgrade/inspección) para el Database Module."""

    def __init__(self, *, alembic_ini_path: Path | str = "alembic.ini") -> None:
        self._alembic_ini_path = Path(alembic_ini_path)

    def upgrade_to_head(self, database_url: str) -> None:
        """Aplica todas las migraciones pendientes hasta la última revisión."""
        command.upgrade(self._config(database_url), "head")

    def downgrade(self, database_url: str, revision: str) -> None:
        """Revierte hasta ``revision`` (p. ej. ``"-1"`` o un id de revisión concreto)."""
        command.downgrade(self._config(database_url), revision)

    def head_revision(self) -> str | None:
        """La última revisión definida en ``database/migrations/versions/``.

        Lee únicamente el directorio de scripts — no abre ninguna conexión
        a base de datos, así que no informa si esa revisión ya está
        aplicada (para eso, ``alembic current`` contra la base real).
        """
        script_directory = ScriptDirectory.from_config(self._config(""))
        return script_directory.get_current_head()

    def _config(self, database_url: str) -> Config:
        config = Config(str(self._alembic_ini_path))
        config.set_main_option("sqlalchemy.url", database_url)
        return config
