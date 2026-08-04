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

Desde Sprint 2.8 (ver ADR-008), ``/health``/``/ready`` evalúan de verdad los
``ModuleHealth`` de cada módulo bootstrapeado (``ModuleBase.bootstrap()``,
``app.state.bootstrapped_modules``) vía ``CompositeHealthChecker``
(``teaf._internal.observability.health.checker``) — cierra la brecha
documentada en ``sdk/health.py`` ("ningún endpoint invoca estas funciones
todavía"). Se leen en cada petición (no en el arranque) porque
``ModuleHealth.check`` es una lectura de caché síncrona y barata (ver
``modules/security/health.py``/``modules/observability/health.py``) — nunca
hace I/O real, así que evaluarla por petición no compromete el requisito de
NFR.md. ``/live`` sigue siendo estática a propósito: liveness solo debe
responder si el proceso está vivo, nunca verificar dependencias (eso
degradaría un contenedor sano solo porque una dependencia está caída,
provocando reinicios en cascada innecesarios).
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from starlette.responses import JSONResponse

from teaf._internal.core.version import VersionInfo
from teaf._internal.observability.health.checker import CompositeHealthChecker
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.sdk.module_base import ModuleBase


def _bootstrapped_modules(request: Request) -> tuple[ModuleBase, ...]:
    return tuple(getattr(request.app.state, "bootstrapped_modules", ()))


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
    def health(request: Request) -> dict[str, object]:
        """Estado general de la instancia, incluyendo el desglose por módulo."""
        report = CompositeHealthChecker.from_modules(_bootstrapped_modules(request)).check_all()
        return {
            "status": "ok" if report.overall is not CapabilityHealth.UNHEALTHY else "degraded",
            "name": version_info.name,
            "version": version_info.version,
            "environment": version_info.environment,
            "buildDate": version_info.build_date or "unknown",
            "modules": report.as_dict(),
        }

    @router.get("/live")
    def live() -> dict[str, str]:
        """Liveness probe: el proceso está vivo y responde — nunca verifica dependencias."""
        return {"status": "alive"}

    @router.get("/ready")
    def ready(request: Request) -> JSONResponse:
        """Readiness probe: ``ready`` solo si ningún ``HealthCheck`` crítico está ``UNHEALTHY``."""
        report = CompositeHealthChecker.from_modules(_bootstrapped_modules(request)).check_all()
        is_ready = report.overall is not CapabilityHealth.UNHEALTHY
        return JSONResponse(
            status_code=200 if is_ready else 503,
            content={"status": "ready" if is_ready else "not_ready", "checks": report.as_dict()},
        )

    return router
