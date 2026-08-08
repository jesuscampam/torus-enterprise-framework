"""``SecurityHeadersMiddleware`` — cabeceras de seguridad HTTP (Sprint 2.9.2, ADR-010).

Implementa [SECURITY-STANDARD.md §7](../../../docs/standards/SECURITY-STANDARD.md):
``Strict-Transport-Security``, ``X-Content-Type-Options``, ``X-Frame-Options``
y ``Content-Security-Policy``. Hasta Sprint 2.9.2 el estándar exigía esas
cuatro cabeceras y ``Settings`` declaraba tres campos para gobernarlas, pero
no existía nada que las emitiera: la configuración comunicaba una protección
inexistente, que es peor que no ofrecerla.

Tres decisiones que no son evidentes:

1. **Middleware ASGI puro, no ``BaseHTTPMiddleware``.** Basta con interceptar
   el mensaje ``http.response.start`` y añadir cabeceras. ``BaseHTTPMiddleware``
   obligaría a materializar el cuerpo de toda respuesta y rompería el
   streaming, a cambio de nada: aquí no se mira el cuerpo. El coste de esta
   implementación es una copia de la lista de cabeceras por respuesta.

2. **HSTS solo sobre HTTPS.** RFC 6797 §7.2 lo exige literalmente: *«An HSTS
   Host MUST NOT include the STS header field in HTTP responses conveyed over
   non-secure transport»*. Emitirla siempre no solo incumpliría la norma —los
   navegadores la ignoran sobre HTTP—, sino que en desarrollo puede fijar el
   dominio ``localhost`` en HTTPS en el navegador del desarrollador durante un
   año. El esquema se lee del *scope* ASGI, que es lo que reescribe uvicorn
   con ``--proxy-headers`` a partir de ``X-Forwarded-Proto``; no se lee la
   cabecera directamente, para no fabricar aquí una segunda vía de confianza
   distinta de la que gobierna ``trust_forwarded_headers`` (ver ADR-010).

3. **La CSP no se aplica a la documentación.** Swagger UI y ReDoc cargan sus
   propios JS y CSS; la CSP por defecto (``default-src 'none'``) los rompería,
   y un desarrollador que se encuentre ``/docs`` en blanco desactivará el
   middleware entero — que es el peor resultado posible. Las demás cabeceras
   sí se aplican también ahí. Es una excepción acotada a rutas de
   documentación, deshabilitadas por defecto en producción.

Nunca se sobrescribe una cabecera que la aplicación ya haya puesto: si un
endpoint fija su propia CSP, manda el endpoint.
"""

from __future__ import annotations

from collections.abc import Iterable

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

#: Rutas de documentación exentas de ``Content-Security-Policy`` (ver
#: docstring del módulo). Coinciden con las que ``create_app`` configura en
#: ``FastAPI(docs_url=..., redoc_url=...)``.
_DOCUMENTATION_PATHS: frozenset[str] = frozenset({"/docs", "/redoc"})

#: Sufijos de ruta de la documentación que sirven HTML auxiliar (por ejemplo
#: ``/docs/oauth2-redirect``).
_DOCUMENTATION_PREFIXES: tuple[str, ...] = ("/docs/", "/redoc/")


def is_documentation_path(path: str) -> bool:
    """``True`` si ``path`` es una ruta de documentación interactiva."""
    return path in _DOCUMENTATION_PATHS or path.startswith(_DOCUMENTATION_PREFIXES)


class SecurityHeadersMiddleware:
    """Añade las cabeceras de seguridad de SECURITY-STANDARD.md §7 a cada respuesta."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        enabled: bool = True,
        hsts_max_age_seconds: int = 31_536_000,
        frame_options: str = "DENY",
        content_security_policy: str = "default-src 'none'; frame-ancestors 'none'",
    ) -> None:
        self.app = app
        self._enabled = enabled
        self._hsts_max_age_seconds = hsts_max_age_seconds
        self._frame_options = frame_options
        self._content_security_policy = content_security_policy

    def headers_for(self, *, path: str, secure: bool) -> tuple[tuple[str, str], ...]:
        """Cabeceras que corresponden a una respuesta para ``path``.

        Se expone como método —en vez de resolverse dentro del ``send``— para
        poder probar la política sin levantar una aplicación, que es lo que
        permite fijar los valores exactos en las pruebas.
        """
        if not self._enabled:
            return ()

        headers: list[tuple[str, str]] = [("x-content-type-options", "nosniff")]

        if self._hsts_max_age_seconds > 0 and secure:
            headers.append(("strict-transport-security", f"max-age={self._hsts_max_age_seconds}"))
        if self._frame_options:
            headers.append(("x-frame-options", self._frame_options))
        if self._content_security_policy and not is_documentation_path(path):
            headers.append(("content-security-policy", self._content_security_policy))

        return tuple(headers)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not self._enabled:
            await self.app(scope, receive, send)
            return

        applicable = self.headers_for(
            path=scope.get("path", ""), secure=scope.get("scheme") == "https"
        )
        if not applicable:
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                _apply(MutableHeaders(scope=message), applicable)
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _apply(headers: MutableHeaders, additions: Iterable[tuple[str, str]]) -> None:
    """Añade ``additions`` sin pisar lo que la aplicación ya haya establecido."""
    for name, value in additions:
        if name not in headers:
            headers[name] = value
