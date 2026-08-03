"""Application Factory — punto de entrada único para construir la aplicación.

Implementa el patrón Application Factory (ver
docs/architecture/FRAMEWORK-BLUEPRINT.md, Sprint 2.1, ítem 1) y orquesta el
flujo de inicialización documentado en la sección 7 del blueprint: carga de
configuración, logging, middlewares, rutas base, DI y exposición de
información de versión. Desde Sprint 2.3 (Runtime), también construye el
``Runtime`` y lo conecta al ciclo de vida de FastAPI vía ``lifespan``.

Nota arquitectónica — excepción explícita a la regla de dependencias:
este módulo es el *composition root* del framework (equivalente al
componente "Main" de Clean Architecture: es el único lugar autorizado a
conocer y conectar todas las capas para ensamblar la aplicación). Por eso,
y solo aquí, se permite importar ``backend/config/``, ``backend/middleware/``,
``backend/monitoring/``, ``backend/providers/`` y ``backend/runtime/`` desde
dentro de ``backend/core/`` — el resto de los archivos de ``core/``
(``exceptions.py``, ``context.py``, ``logging.py``, ``version.py``,
``dependencies.py``, ``registry.py``) permanecen, como exige la regla 1 de
la sección 11 del blueprint, sin ninguna dependencia de otro módulo.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from backend.config.environment import Environment
from backend.config.settings import Settings, get_settings
from backend.core.logging import configure_logging, get_logger
from backend.core.registry import ModuleDescriptor, ModuleRegistry, ModuleStatus
from backend.core.version import get_version_info
from backend.developer.runtime_api import DeveloperRuntimeAPI
from backend.middleware.exception_handler import register_exception_handlers
from backend.middleware.logging import RequestLoggingMiddleware
from backend.middleware.request_id import RequestIdMiddleware
from backend.monitoring.health import create_health_router
from backend.monitoring.info import create_info_router
from backend.runtime.api import create_runtime_router
from backend.runtime.manifest import write_manifest
from backend.runtime.runtime import Runtime
from backend.shared.constants import DEFAULT_SERVICE_NAME

#: Versión del propio framework TEAF (no de una aplicación construida sobre
#: él). Se actualiza junto con CHANGELOG.md en cada release (ver
#: docs/standards/GIT-STANDARD.md, sección 6, Versionado Semántico).
FRAMEWORK_VERSION = "0.6.0-alpha"

#: Raíz del repositorio, para escribir ``runtime.manifest.json`` (ver
#: Sprint 2.4, ítem 9) siempre en el mismo lugar sin depender del directorio
#: de trabajo desde el que se lance el proceso.
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

#: Subsistemas de infraestructura que en Sprint 2.2 solo tienen contratos y
#: clases base (``backend/contracts/`` + ``backend/providers/``) — sin
#: implementación ni conexión real. ``dependencies`` refleja las reglas ya
#: fijadas en FRAMEWORK-BLUEPRINT.md, sección 5 (AI depende de Security);
#: el ``DependencyGraph`` del Runtime las usa para detectar ciclos antes de
#: arrancar.
_INFRASTRUCTURE_MODULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("database", ()),
    ("security", ()),
    ("telemetry", ()),
    ("storage", ()),
    ("ai", ("security",)),
    ("scheduler", ()),
    ("notification", ()),
)


def _configuration_summary(settings: Settings) -> Mapping[str, object]:
    """Resumen serializable y no sensible de la configuración activa.

    Expuesto vía ``GET /runtime/configuration`` y ``runtime.manifest.json``.
    Ningún campo de ``Settings`` actual es un secreto (ver
    ``backend/config/settings.py``) — si un Sprint futuro añade credenciales
    reales, deberá excluirlas explícitamente de este resumen antes de
    exponerlas.
    """
    return {
        "appName": settings.app_name,
        "environment": settings.environment.value,
        "debug": settings.debug,
        "host": settings.host,
        "port": settings.port,
        "logLevel": settings.log_level,
        "logFormat": settings.log_format,
        "docsEnabled": settings.docs_enabled,
    }


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Conecta el ``Runtime`` al ciclo de vida de FastAPI (startup/shutdown)."""
    runtime: Runtime = app.state.runtime
    await runtime.startup()

    # El manifiesto es un artefacto de despliegue (ver Sprint 2.4, ítem 9) —
    # no tiene sentido regenerarlo en cada instancia efímera de test, y un
    # filesystem de solo lectura en producción no debe tumbar el arranque.
    settings: Settings = app.state.settings
    if settings.environment is not Environment.TESTING:
        try:
            write_manifest(
                runtime,
                _REPOSITORY_ROOT / "runtime.manifest.json",
                configuration_summary=dict(app.state.configuration_summary),
            )
        except OSError as exc:
            get_logger("teaf.runtime").warning(
                "runtime_manifest_write_failed", extra={"context": {"error": str(exc)}}
            )

    try:
        yield
    finally:
        await runtime.shutdown()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construye y configura la instancia de FastAPI del framework.

    Args:
        settings: Configuración a usar. Si se omite, se resuelve con
            ``get_settings()`` (permite inyectar una configuración distinta
            en pruebas sin depender de variables de entorno globales).
    """
    settings = settings or get_settings()
    configuration_summary = _configuration_summary(settings)

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
        lifespan=_lifespan,
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

    # ``settings``/``configuration_summary`` viven en app.state para que
    # ``_lifespan`` (que solo recibe ``app``) pueda leerlos sin capturarlos
    # como variables libres de un closure — mismo criterio que
    # ``module_registry``/``runtime`` más abajo.
    app.state.settings = settings
    app.state.configuration_summary = configuration_summary

    registry = ModuleRegistry()
    for module_name, module_dependencies in _INFRASTRUCTURE_MODULES:
        registry.register(
            ModuleDescriptor(
                name=module_name,
                version=FRAMEWORK_VERSION,
                status=ModuleStatus.CONTRACTS_ONLY,
                dependencies=module_dependencies,
            )
        )
    # Expuesto vía app.state (no como singleton de proceso) para que cada
    # instancia de aplicación tenga su propio registro aislado — ver la nota
    # de diseño en backend/core/registry.py. Los routers lo consumen vía
    # Depends(get_module_registry) (backend/providers/dependencies.py).
    app.state.module_registry = registry

    # Igual que module_registry: un Runtime por instancia de aplicación, no
    # un singleton de proceso — arranca/se apaga vía _lifespan más arriba.
    runtime = Runtime(registry=registry, framework_version=FRAMEWORK_VERSION)
    app.state.runtime = runtime
    # Fachada de consumo directo (sin HTTP) del mismo Runtime — ver Sprint 2.4,
    # ítem 13. No se expone por ningún router; queda disponible en app.state
    # para scripts/consolas/plugins que corran en el mismo proceso.
    app.state.developer_api = DeveloperRuntimeAPI(
        runtime, configuration_provider=lambda: configuration_summary
    )

    app.include_router(
        create_info_router(version_info, registry, lambda: runtime.describe().as_dict())
    )
    app.include_router(
        create_runtime_router(runtime, configuration_provider=lambda: configuration_summary)
    )

    logger.info("application_bootstrap_completed")
    return app
