"""Rutas de sistema: bienvenida, health, liveness y readiness.

Implementa el requisito de NFR.md ("Health Check responde en <5s") y el
flujo de arranque de docs/architecture/FRAMEWORK-BLUEPRINT.md, sección 7.
No son endpoints versionados de negocio (``/api/v1/...``): son sondas de
infraestructura consumidas por el orquestador (Docker, Azure App Service),
por eso viven fuera del prefijo de API.

Este módulo depende únicamente de ``backend/core/version.py`` (Core) — no
importa ``backend/config/`` directamente, para no violar la regla "Monitoring
depende únicamente de Core" (ver FRAMEWORK-BLUEPRINT.md, sección 11, regla
2). Es el composition root (``backend/core/application.py``) quien resuelve
el ``VersionInfo`` real a partir de la configuración y lo inyecta aquí.

Sin verificaciones reales de dependencias externas todavía (no hay base de
datos ni servicios externos en Sprint 2.1); ``/ready`` y ``/live`` responden
de forma estática. Se ampliarán cuando existan dependencias que verificar.
"""

from __future__ import annotations

from fastapi import APIRouter

from teaf._internal.core.version import VersionInfo


def create_health_router(version_info: VersionInfo) -> APIRouter:
    """Construye el router de rutas de sistema para la instancia en ejecución."""
    router = APIRouter(tags=["system"])

    @router.get("/")
    def root() -> dict[str, str]:
        """Bienvenida mínima con la identidad de la instancia."""
        return {
            "name": version_info.name,
            "version": version_info.version,
            "environment": version_info.environment,
        }

    @router.get("/health")
    def health() -> dict[str, str]:
        """Estado general de la instancia."""
        return {
            "status": "ok",
            "name": version_info.name,
            "version": version_info.version,
            "environment": version_info.environment,
            "buildDate": version_info.build_date or "unknown",
        }

    @router.get("/live")
    def live() -> dict[str, str]:
        """Liveness probe: el proceso está vivo y responde."""
        return {"status": "alive"}

    @router.get("/ready")
    def ready() -> dict[str, str]:
        """Readiness probe: la instancia está lista para recibir tráfico.

        Estática en Sprint 2.1 — cuando existan dependencias reales
        (base de datos, colas, etc.) esta ruta deberá verificarlas antes
        de responder ``ready``.
        """
        return {"status": "ready"}

    return router
