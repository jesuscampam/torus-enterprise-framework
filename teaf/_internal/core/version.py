"""Información de versión de la instancia en ejecución.

Expuesta por ``backend/monitoring/health.py`` en las rutas de sistema.
Deliberadamente sin dependencias de ``config/``: recibe sus valores como
parámetros (ver nota de independencia en ``backend/core/logging.py``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class VersionInfo:
    """Identidad de la instancia del framework en ejecución."""

    name: str
    version: str
    environment: str
    #: Fecha de compilación de la imagen. Placeholder hasta que exista un
    #: pipeline de build real que la inyecte (ver docker/README.md).
    build_date: str | None = None


def get_version_info(
    *, name: str, version: str, environment: str, build_date: str | None = None
) -> VersionInfo:
    """Construye la información de versión a partir de los valores resueltos por config/."""
    return VersionInfo(name=name, version=version, environment=environment, build_date=build_date)
