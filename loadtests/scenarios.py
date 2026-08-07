"""Los nueve escenarios de carga de TEAF (Sprint 2.9.1).

Cada escenario levanta la aplicación con **un** subsistema en el camino de
la petición, para que su coste se pueda atribuir por resta.

Para que esa resta signifique algo, cada escenario tiene su control
explícito, y **solo se comparan los pares indicados**:

| Escenario | Se compara contra | Lo que mide la diferencia |
|---|---|---|
| `security` | `health` | Coste del middleware de seguridad. |
| `rate-limit` | `health` | Coste de comprobar el límite. |
| `rate-limit-rejecting` | `rate-limit` | Coste de rechazar frente a atender. |
| `logging` | `baseline` | Coste de un log estructurado por petición. |
| `tracing` | `baseline` | Coste de un span por petición. |
| `health`, `info`, `runtime` | — | Cifras absolutas de los endpoints de sistema. |

`baseline` existe justamente para eso: es una ruta trivial sobre la misma
``Application``, sin la que `logging` y `tracing` parecerían más rápidos que
`health` — no por ser gratis, sino porque `/health` ejecuta comprobaciones
de salud reales y una ruta trivial no. Comparar contra el control
equivocado es la forma más fácil de sacar una conclusión al revés.

Los escenarios no comprueban comportamiento — de eso se ocupan
``tests/integration/``. Aquí solo se cuenta que la respuesta sea la
esperada, porque un escenario que devuelve 500 a toda velocidad mediría el
coste del manejador de errores y parecería excelente.
"""

from __future__ import annotations

import logging

from teaf import Application, Configuration
from teaf.api import ApiGateway, ProtectionScope, RateLimiter, RateLimitRule
from teaf.observability import OtelTracer, SpanKind
from teaf.security import (
    AnonymousIdentityProvider,
    IdentityProviderRegistry,
    PrincipalResolver,
    SecurityMiddleware,
    StaticRoleResolver,
)

from loadtests.harness import LoadScenario


def _load_configuration() -> Configuration:
    """Configuración explícita, sin heredar la del entorno.

    Se construye con la API pública (``Configuration``, no la clase interna
    ``TestingSettings``) por la misma razón que se le exige a los ejemplos:
    si medir el framework obligara a saltarse su propia frontera, la
    frontera estaría mal puesta. ``log_level`` en ``WARNING`` evita que el
    escenario de logging quede enmascarado por el log de acceso de todos
    los demás.
    """
    return Configuration(log_level="WARNING", debug=False)


def _plain_application() -> object:
    """La aplicación tal cual: los endpoints de sistema y nada más."""
    return Application(settings=_load_configuration()).asgi


def _baseline_application() -> object:
    """Ruta trivial sobre ``Application``: el control de `logging` y `tracing`.

    Devuelve lo mismo que ellos y no hace nada más, así que la diferencia
    de rendimiento es atribuible al subsistema y no a la forma de la
    respuesta ni al enrutado.
    """
    application = Application(settings=_load_configuration())

    @application.asgi.get("/carga/nada")
    async def nada() -> dict[str, str]:
        return {"status": "ok"}

    return application.asgi


def _secured_application() -> object:
    """Aplicación con ``SecurityMiddleware`` resolviendo identidad en cada petición.

    Se usa el proveedor anónimo a propósito: mide el coste fijo de la
    cadena de seguridad (resolución de identidad, construcción del
    ``Principal``, contexto) sin mezclarlo con el de verificar una firma
    JWT o consultar un LDAP, que dependen de la configuración de cada
    aplicación y no del framework.
    """
    application = Application(settings=_load_configuration())
    application.asgi.add_middleware(
        SecurityMiddleware,
        provider_registry=IdentityProviderRegistry([AnonymousIdentityProvider()]),
        principal_resolver=PrincipalResolver(role_resolver=StaticRoleResolver(roles_by_name={})),
    )
    return application.asgi


def _logging_application() -> object:
    """Aplicación que emite un log estructurado por petición."""
    application = Application(settings=_load_configuration())
    logger = logging.getLogger("loadtests.logging")
    logger.setLevel(logging.INFO)
    #: Sin manejadores: se mide el coste de construir y filtrar el registro,
    #: no el de escribir en un disco cuya velocidad no es del framework.
    logger.handlers.clear()
    logger.propagate = False

    @application.asgi.get("/carga/log")
    async def emitir() -> dict[str, str]:
        logger.info("petición procesada", extra={"escenario": "carga", "resultado": "ok"})
        return {"status": "ok"}

    return application.asgi


def _tracing_application() -> object:
    """Aplicación que abre y cierra un span real de OpenTelemetry por petición."""
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415

    application = Application(settings=_load_configuration())
    #: ``TracerProvider`` sin exportador: mide la creación del span y su
    #: contexto, no la latencia de red de mandarlo a un colector.
    tracer = OtelTracer(TracerProvider().get_tracer("loadtests"))

    @application.asgi.get("/carga/traza")
    async def trazar() -> dict[str, str]:
        with tracer.start_span("carga", kind=SpanKind.SERVER):
            return {"status": "ok"}

    return application.asgi


def _rate_limited(limit: int) -> object:
    """``Application`` con el limitador instalado, atacando ``GET /health``.

    Se monta sobre ``Application`` y no sobre un ``FastAPI`` desnudo — y se
    ataca el mismo endpoint que el escenario ``health`` — precisamente para
    que la resta contra ``health`` signifique algo. Una primera versión de
    esta suite usaba un ``FastAPI`` con una sola ruta trivial, y salía
    «más rápida» que la aplicación completa: no medía el coste del
    limitador, medía la ausencia del resto del framework.
    """
    application = Application(settings=_load_configuration())
    ApiGateway(
        rate_limiter=RateLimiter(
            [
                RateLimitRule(
                    name="carga",
                    limit=limit,
                    window_seconds=3_600.0,
                    scope=ProtectionScope.IP,
                )
            ]
        )
    ).install(application.asgi)
    return application.asgi


def _rate_limited_application() -> object:
    """Límite inalcanzable: mide el coste de **comprobar**, que lo paga el 100% del tráfico."""
    return _rate_limited(limit=10_000_000)


def _rate_limited_rejecting_application() -> object:
    """La otra mitad de la historia: el camino de rechazo, saturado.

    Un limitador solo cumple su función si rechazar es **más barato** que
    atender; si no, un atacante lo usa como amplificador. Este escenario
    existe para tener ese número, no por simetría.
    """
    return _rate_limited(limit=1)


ALL_SCENARIOS: tuple[LoadScenario, ...] = (
    LoadScenario(
        name="health",
        description="GET /health — línea base: la aplicación desnuda.",
        build=_plain_application,
        path="/health",
    ),
    LoadScenario(
        name="info",
        description="GET /info — metadatos de la aplicación y sus módulos.",
        build=_plain_application,
        path="/info",
    ),
    LoadScenario(
        name="runtime",
        description="GET /runtime/info — introspección del Runtime.",
        build=_plain_application,
        path="/runtime/info",
    ),
    LoadScenario(
        name="security",
        description="GET /health tras SecurityMiddleware (identidad anónima).",
        build=_secured_application,
        path="/health",
    ),
    LoadScenario(
        name="baseline",
        description="Ruta trivial — control de `logging` y `tracing`.",
        build=_baseline_application,
        path="/carga/nada",
    ),
    LoadScenario(
        name="logging",
        description="Un log estructurado por petición.",
        build=_logging_application,
        path="/carga/log",
    ),
    LoadScenario(
        name="tracing",
        description="Un span de OpenTelemetry por petición.",
        build=_tracing_application,
        path="/carga/traza",
    ),
    LoadScenario(
        name="rate-limit",
        description="Comprobación del límite en cada petición (sin rechazar).",
        build=_rate_limited_application,
        path="/health",
    ),
    LoadScenario(
        name="rate-limit-rejecting",
        description="Camino de rechazo 429 saturado — debe ser más barato que atender.",
        build=_rate_limited_rejecting_application,
        path="/health",
        expected_status=429,
    ),
)
