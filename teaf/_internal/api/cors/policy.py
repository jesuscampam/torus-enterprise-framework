"""``CorsPolicy`` — política CORS configurable (Sprint 2.9, ADR-009).

Deliberadamente **no** se usa ``starlette.middleware.cors.CORSMiddleware``,
aunque exista: TEAF necesita que la política CORS sea un objeto de dominio
inspeccionable y componible (declarable en configuración, consultable desde
el manifiesto del módulo, evaluable en pruebas sin levantar un servidor) y
con soporte de comodines de subdominio (``https://*.torus.com``), que el
middleware de Starlette no ofrece. ``CorsPolicy`` es ese objeto; el
middleware que lo aplica es una capa fina encima
(``api/middleware/cors.py``), igual que en el resto de la plataforma.

Regla de seguridad no negociable, heredada del propio estándar CORS: con
``allow_credentials=True`` nunca se responde ``Access-Control-Allow-Origin:
*`` — se responde con el origen concreto solicitado. Un navegador rechaza
esa combinación, y "arreglarla" devolviendo el comodín convertiría cualquier
web en cliente autenticado de la API (ver docs/api/CORS.md).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

#: Cabeceras que un navegador siempre puede enviar sin declararlas en la
#: petición de comprobación previa (preflight) — no hace falta listarlas en
#: ``allow_headers`` para que funcionen.
_SIMPLE_HEADERS = frozenset({"accept", "accept-language", "content-language", "content-type"})


def _origin_matches(pattern: str, origin: str) -> bool:
    """``True`` si ``origin`` encaja con ``pattern`` (``*``, exacto o ``https://*.dominio``)."""
    if pattern == "*":
        return True
    if pattern == origin:
        return True
    scheme_sep = "://"
    if "*" not in pattern or scheme_sep not in pattern:
        return False
    pattern_scheme, _, pattern_host = pattern.partition(scheme_sep)
    origin_scheme, _, origin_host = origin.partition(scheme_sep)
    if pattern_scheme != origin_scheme or not pattern_host.startswith("*."):
        return False
    # "https://*.torus.com" acepta "https://app.torus.com" pero no
    # "https://torus.com" ni "https://evil-torus.com".
    return origin_host.endswith(pattern_host[1:]) and origin_host != pattern_host[2:]


@dataclass(frozen=True, slots=True)
class CorsPolicy:
    """Qué orígenes, métodos y cabeceras cruzadas admite la API.

    Los valores por defecto son los más restrictivos posibles (ningún origen
    permitido): habilitar la plataforma de protección nunca debe abrir CORS
    por accidente — quien lo necesita lo declara explícitamente.
    """

    allow_origins: tuple[str, ...] = ()
    allow_methods: tuple[str, ...] = ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS")
    allow_headers: tuple[str, ...] = ()
    expose_headers: tuple[str, ...] = ()
    allow_credentials: bool = False
    max_age_seconds: int = 600
    #: Orígenes con comodín de subdominio, separados del resto solo por
    #: legibilidad — ``allow_origins`` también los admite.
    allow_origin_patterns: tuple[str, ...] = field(default_factory=tuple)

    @property
    def enabled(self) -> bool:
        """``True`` si hay al menos un origen permitido."""
        return bool(self.allow_origins or self.allow_origin_patterns)

    @property
    def allows_any_origin(self) -> bool:
        """``True`` si la política admite cualquier origen (``"*"``)."""
        return "*" in self.allow_origins

    def is_origin_allowed(self, origin: str) -> bool:
        """``True`` si ``origin`` está permitido por la política."""
        candidates: Sequence[str] = (*self.allow_origins, *self.allow_origin_patterns)
        return any(_origin_matches(pattern, origin) for pattern in candidates)

    def is_method_allowed(self, method: str) -> bool:
        """``True`` si ``method`` está permitido en peticiones cruzadas."""
        return "*" in self.allow_methods or method.upper() in {
            m.upper() for m in self.allow_methods
        }

    def are_headers_allowed(self, headers: Sequence[str]) -> bool:
        """``True`` si todas las cabeceras solicitadas están permitidas."""
        if "*" in self.allow_headers:
            return True
        allowed = {h.lower() for h in self.allow_headers} | _SIMPLE_HEADERS
        return all(header.strip().lower() in allowed for header in headers if header.strip())

    def _allow_origin_value(self, origin: str) -> str:
        """Valor de ``Access-Control-Allow-Origin``: el comodín, o el origen concreto.

        Con credenciales activadas siempre devuelve el origen concreto — ver
        la nota de seguridad del docstring del módulo.
        """
        if self.allows_any_origin and not self.allow_credentials:
            return "*"
        return origin

    def preflight_headers(
        self, origin: str, *, request_method: str, request_headers: Sequence[str] = ()
    ) -> dict[str, str] | None:
        """Cabeceras de respuesta a un preflight ``OPTIONS``, o ``None`` si no se admite.

        Devolver ``None`` (en vez de lanzar) deja que el middleware responda
        403 sin cabeceras CORS, que es exactamente lo que el navegador
        interpreta como "origen no autorizado".
        """
        if not self.is_origin_allowed(origin):
            return None
        if not self.is_method_allowed(request_method):
            return None
        if not self.are_headers_allowed(request_headers):
            return None

        headers = {
            "Access-Control-Allow-Origin": self._allow_origin_value(origin),
            "Access-Control-Allow-Methods": ", ".join(self.allow_methods),
            "Access-Control-Max-Age": str(self.max_age_seconds),
        }
        requested = [h.strip() for h in request_headers if h.strip()]
        if requested:
            headers["Access-Control-Allow-Headers"] = ", ".join(requested)
        elif self.allow_headers:
            headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        # Sin "Vary: Origin" una caché intermedia podría servir la respuesta
        # de un origen permitido a otro que no lo está.
        headers["Vary"] = "Origin"
        return headers

    def response_headers(self, origin: str) -> dict[str, str]:
        """Cabeceras CORS de una respuesta normal (no preflight); vacío si no se admite."""
        if not self.is_origin_allowed(origin):
            return {}
        headers = {
            "Access-Control-Allow-Origin": self._allow_origin_value(origin),
            "Vary": "Origin",
        }
        if self.allow_credentials:
            headers["Access-Control-Allow-Credentials"] = "true"
        if self.expose_headers:
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
        return headers
