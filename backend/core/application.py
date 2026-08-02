"""Application Factory — punto de entrada único para construir la aplicación.

Implementa el patrón Application Factory (ver
docs/architecture/FRAMEWORK-BLUEPRINT.md, Sprint 2.1, ítem 1) y orquesta el
flujo de inicialización documentado en la sección 7 del blueprint: carga de
configuración, logging, middlewares, rutas base, DI y exposición de
información de versión.

Nota arquitectónica — excepción explícita a la regla de dependencias:
este módulo es el *composition root* del framework (equivalente al
componente "Main" de Clean Architecture: es el único lugar autorizado a
conocer y conectar todas las capas para ensamblar la aplicación). Por eso,
y solo aquí, se permite importar ``backend/config/``, ``backend/middleware/``
y ``backend/monitoring/`` desde dentro de ``backend/core/`` — el resto de
los archivos de ``core/`` (``exceptions.py``, ``context.py``, ``logging.py``,
``version.py``, ``dependencies.py``) permanecen, como exige la regla 1 de la
sección 11 del blueprint, sin ninguna dependencia de otro módulo.
"""

from __future__ import annotations

from fastapi import FastAPI

from backend.config.settings import Settings, get_settings
from backend.core.logging import configure_logging, get_logger
from backend.core.version import get_version_info
from backend.middleware.exception_handler import register_exception_handlers
from backend.middleware.logging import RequestLoggingMiddleware
from backend.middleware.request_id import RequestIdMiddleware
from backend.monitoring.health import create_health_router
from backend.shared.constants import DEFAULT_SERVICE_NAME

#: Versión del propio framework TEAF (no de una aplicación construida sobre
#: él). Se actualiza junto con CHANGELOG.md en cada release (ver
#: docs/standards/GIT-STANDARD.md, sección 6, Versionado Semántico).
FRAMEWORK_VERSION = "0.1.0"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye y configura la instancia de FastAPI del framework.

    Args:
        settings: Configuración a usar. Si se omite, se resuelve con
            ``get_settings()`` (permite inyectar una configuración distinta
            en pruebas sin depender de variables de entorno globales).
    """
    settings = settings or get_settings()

    configure_logging(
        level=settings.log_level,
        log_format=settings.log_format,
        service_name=DEFAULT_SERVICE_NAME,
        log_file=settings.log_file,
    )
    logger = get_logger("teaf.bootstrap")
    logger.info(
        "application_bootstrap_started",
        extra={"context": {"environment": settings.environment}},
    )

    app = FastAPI(
        title=settings.app_name,
        version=FRAMEWORK_VERSION,
        debug=settings.debug,
        docs_url="/docs" if settings.docs_enabled else None,
        redoc_url="/redoc" if settings.docs_enabled else None,
        openapi_url="/openapi.json" if settings.docs_enabled else None,
    )

    # El orden de registro importa: Starlette ejecuta los middlewares en
    # orden inverso al que se añaden (el último añadido es el más externo).
    # RequestIdMiddleware debe ejecutarse antes que RequestLoggingMiddleware
    # para que el correlation-id ya esté disponible al loguear la petición.
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIdMiddleware)

    register_exception_handlers(app)

    version_info = get_version_info(
        name=settings.app_name,
        version=FRAMEWORK_VERSION,
        environment=settings.environment.value,
    )
    app.include_router(create_health_router(version_info))

    logger.info("application_bootstrap_completed")
    return app
