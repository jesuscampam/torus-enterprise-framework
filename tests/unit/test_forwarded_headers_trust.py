"""Pruebas de confianza en cabeceras de reenvío (Sprint 2.9.2, ADR-010, H-2).

Demuestran la diferencia entre los dos despliegues que el framework no puede
distinguir por sí mismo:

    proxy de confianza          cliente directo (no fiable)
    ─────────────────           ───────────────────────────
    X-Forwarded-For la          X-Forwarded-For la controla
    reescribe el proxy          el atacante
            │                             │
            ▼                             ▼
    IP real del cliente         IP falsificable

Con ``trust_forwarded_headers=True`` la cabecera manda; con ``False`` se
ignora y se usa la IP de la conexión. La prueba que importa es la segunda:
verifica que un atacante **no puede** repartirse entre cubetas de rate
limiting inventando IPs cuando la configuración no lo permite.
"""

from __future__ import annotations

import asyncio
import logging

from starlette.requests import Request
from teaf._internal.api.middleware.context import build_request_context, resolve_client_ip
from teaf.api import ApiGateway, ProtectionScope, RateLimiter, RateLimitRule

#: IP de la conexión TCP real — la que un atacante no puede falsificar.
CONEXION_REAL = "10.0.0.1"
#: IP que el cliente afirma tener en la cabecera.
IP_AFIRMADA = "203.0.113.99"


def _request(headers: dict[str, str], *, client: str | None = CONEXION_REAL) -> Request:
    """Petición ASGI mínima con las cabeceras y la IP de conexión dadas."""
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/recurso",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "query_string": b"",
        "client": (client, 12345) if client else None,
        "scheme": "http",
        "server": ("testserver", 80),
    }
    return Request(scope)  # type: ignore[arg-type]


# -- resolve_client_ip --------------------------------------------------------------------


def test_forwarded_header_is_used_when_trusted() -> None:
    """Detrás de un proxy que la reescribe, la cabecera es la fuente correcta."""
    request = _request({"X-Forwarded-For": IP_AFIRMADA})
    assert resolve_client_ip(request, trust_forwarded_headers=True) == IP_AFIRMADA


def test_forwarded_header_is_ignored_when_not_trusted() -> None:
    """Sin proxy de confianza, manda la conexión: la cabecera no se cree."""
    request = _request({"X-Forwarded-For": IP_AFIRMADA})
    assert resolve_client_ip(request, trust_forwarded_headers=False) == CONEXION_REAL


def test_real_ip_header_is_also_ignored_when_not_trusted() -> None:
    request = _request({"X-Real-IP": IP_AFIRMADA})
    assert resolve_client_ip(request, trust_forwarded_headers=False) == CONEXION_REAL


def test_first_entry_of_the_forwarded_chain_is_the_client() -> None:
    request = _request({"X-Forwarded-For": f"{IP_AFIRMADA}, 10.1.1.1, 10.1.1.2"})
    assert resolve_client_ip(request, trust_forwarded_headers=True) == IP_AFIRMADA


def test_falls_back_to_the_connection_when_no_forwarded_header_exists() -> None:
    assert resolve_client_ip(_request({}), trust_forwarded_headers=True) == CONEXION_REAL


def test_returns_none_when_there_is_no_client_and_no_trusted_header() -> None:
    assert resolve_client_ip(_request({}, client=None), trust_forwarded_headers=False) is None


def test_request_context_carries_the_resolved_ip() -> None:
    context = build_request_context(
        _request({"X-Forwarded-For": IP_AFIRMADA}), trust_forwarded_headers=False
    )
    assert context.client_ip == CONEXION_REAL


# -- Efecto real sobre el limitador -------------------------------------------------------


def _agotar_limite(*, trust: bool, cabeceras: list[dict[str, str]]) -> list[bool]:
    """Lanza una petición por cada juego de cabeceras. Devuelve si fue aceptada."""

    async def _run() -> list[bool]:
        limiter = RateLimiter(
            [RateLimitRule(name="por-ip", limit=2, window_seconds=60.0, scope=ProtectionScope.IP)]
        )
        aceptadas: list[bool] = []
        for cabecera in cabeceras:
            context = build_request_context(_request(cabecera), trust_forwarded_headers=trust)
            aceptadas.append(await limiter.acquire(context) is None)
        return aceptadas

    return asyncio.run(_run())


def test_spoofing_bypasses_the_rate_limit_when_headers_are_trusted() -> None:
    """Documenta el riesgo: confiando en la cabecera, cada IP inventada es una cubeta nueva.

    No es un fallo de la implementación —es el comportamiento correcto detrás
    de un proxy— sino exactamente la razón por la que ``trust_forwarded_headers``
    no debe dejarse activo sin un proxy delante.
    """
    cabeceras = [{"X-Forwarded-For": f"203.0.113.{n}"} for n in range(5)]
    assert _agotar_limite(trust=True, cabeceras=cabeceras) == [True] * 5


def test_spoofing_does_not_bypass_the_rate_limit_when_headers_are_untrusted() -> None:
    """La prueba que importa: sin confianza, las 5 peticiones caen en la misma cubeta."""
    cabeceras = [{"X-Forwarded-For": f"203.0.113.{n}"} for n in range(5)]
    aceptadas = _agotar_limite(trust=False, cabeceras=cabeceras)
    assert aceptadas == [True, True, False, False, False]


# -- Aviso de despliegue inseguro ---------------------------------------------------------


class _AppFalsa:
    def __init__(self) -> None:
        self.middlewares: list[object] = []

    def add_middleware(self, middleware_class: object, **options: object) -> None:
        self.middlewares.append(middleware_class)


def _instalar(*, trust: bool, con_limitador: bool = True) -> ApiGateway:
    limiter = (
        RateLimiter([RateLimitRule(name="r", limit=10, window_seconds=60.0)])
        if con_limitador
        else None
    )
    gateway = ApiGateway(rate_limiter=limiter, trust_forwarded_headers=trust)
    gateway.install(_AppFalsa())
    return gateway


def _avisos_al_instalar(*, trust: bool, con_limitador: bool = True) -> list[str]:
    """Mensajes emitidos por ``teaf.api.gateway`` durante ``install()``.

    Se engancha un manejador directamente al logger en vez de usar ``caplog``:
    ``configure_logging`` ajusta la propagación de los loggers del framework,
    así que depender de que el registro llegue a la raíz hace que la prueba
    pase o falle según qué otra prueba se haya ejecutado antes.
    """
    registros: list[str] = []

    class _Captura(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            registros.append(record.getMessage())

    logger = logging.getLogger("teaf.api.gateway")
    handler = _Captura()
    nivel_previo = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.WARNING)
    try:
        _instalar(trust=trust, con_limitador=con_limitador)
    finally:
        logger.removeHandler(handler)
        logger.setLevel(nivel_previo)
    return registros


def test_install_warns_when_forwarded_headers_are_trusted() -> None:
    """Un despliegue potencialmente inseguro no debe aceptarse en silencio."""
    assert any("forwarded_headers_trusted" in m for m in _avisos_al_instalar(trust=True))


def test_install_does_not_warn_when_headers_are_untrusted() -> None:
    assert not [m for m in _avisos_al_instalar(trust=False) if "forwarded_headers_trusted" in m]


def test_install_does_not_warn_when_no_middleware_uses_the_client_ip() -> None:
    """Sin limitador, cuotas ni auditoría, la confianza no tiene efecto — no hay nada que avisar."""
    avisos = _avisos_al_instalar(trust=True, con_limitador=False)
    assert not [m for m in avisos if "forwarded_headers_trusted" in m]


def test_running_migrations_does_not_silence_the_framework_loggers() -> None:
    """Regresión de Sprint 2.9.2: ``fileConfig`` desactivaba todos los loggers.

    ``database/migrations/env.py`` llama a ``logging.config.fileConfig``, cuyo
    valor por defecto es ``disable_existing_loggers=True``. Como
    ``DatabaseInstaller`` permite ejecutar migraciones dentro del proceso de
    la aplicación, arrancar con migraciones dejaba mudo al framework entero a
    partir de ese punto: logging de peticiones, auditoría y este mismo aviso
    de seguridad.

    El fallo es silencioso por naturaleza —nada falla, simplemente dejan de
    aparecer registros— así que se fija aquí.
    """
    from logging.config import fileConfig  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    logger = logging.getLogger("teaf.api.gateway")
    logger.warning("previo al fileConfig")

    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    fileConfig(str(alembic_ini), disable_existing_loggers=False)

    assert logger.disabled is False
    assert any("forwarded_headers_trusted" in m for m in _avisos_al_instalar(trust=True))
