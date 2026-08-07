"""``SecurityMiddleware`` — resuelve identidad y publica el ``SecurityContext`` de cada petición.

Mismo patrón que ``middleware/request_id.py``/``middleware/logging.py``
(``BaseHTTPMiddleware``, sin resetear el ``ContextVar`` tras ``call_next``
— cada petición ASGI corre en su propia ``asyncio.Task``, así que no hay
fuga entre peticiones concurrentes).

Nunca bloquea una petición por falta de autenticación — eso es
responsabilidad de ``@authorize()``/``@allow_anonymous()``
(``decorators.py``), aplicados por endpoint. El middleware solo garantiza
que, para toda petición, exista un ``SecurityContext`` resuelto (autenticado
o anónimo) antes de que la petición llegue al handler.
"""

from __future__ import annotations

import base64
from collections.abc import Awaitable, Callable

import jwt as pyjwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from teaf._internal.core.context import get_correlation_id
from teaf._internal.core.exceptions import AuthenticationException
from teaf._internal.core.logging import get_logger
from teaf._internal.providers.security.security_context import set_security_context
from teaf._internal.runtime.event_bus import Event, EventBus
from teaf._internal.security.authorization.rbac import PrincipalResolver
from teaf._internal.security.context import build_security_context
from teaf._internal.security.identity_providers.registry import IdentityProviderRegistry
from teaf._internal.security.models import ANONYMOUS_PRINCIPAL, AuthenticationCredentials

#: Emisores OIDC de Microsoft — usado para enrutar un bearer token hacia el
#: proveedor 'azure-ad' en vez de 'jwt' sin necesitar verificar su firma
#: todavía (la verificación real ocurre en ``IdentityProvider.authenticate``).
_AZURE_AD_ISSUER_HINT = "login.microsoftonline.com"


def _sniff_bearer_scheme(token: str) -> str:
    """Determina qué ``IdentityProvider`` debe recibir este bearer token.

    Decodifica el token **sin verificar su firma** (``verify_signature=False``)
    únicamente para leer el claim ``iss`` y decidir el enrutamiento — la
    verificación criptográfica real ocurre después, dentro de
    ``IdentityProvider.authenticate()``. Un token malformado o sin ``iss``
    se enruta a ``"jwt"`` por defecto (el proveedor rechazará el token si no
    es válido).
    """
    try:
        unverified = pyjwt.decode(
            token, options={"verify_signature": False, "verify_aud": False, "verify_exp": False}
        )
    except pyjwt.PyJWTError:
        return "jwt"
    issuer = str(unverified.get("iss", ""))
    if _AZURE_AD_ISSUER_HINT in issuer:
        return "azure-ad"
    return "jwt"


def _decode_basic_auth(value: str) -> tuple[str | None, str | None]:
    try:
        decoded = base64.b64decode(value).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None, None
    username, separator, password = decoded.partition(":")
    if not separator:
        return None, None
    return username, password


class SecurityMiddleware(BaseHTTPMiddleware):
    """Resuelve el proveedor de identidad de cada petición y publica su ``SecurityContext``."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        provider_registry: IdentityProviderRegistry,
        principal_resolver: PrincipalResolver,
        event_bus: EventBus | None = None,
        api_key_header: str = "X-API-Key",
        api_key_query_param: str = "api_key",
    ) -> None:
        super().__init__(app)
        self._registry = provider_registry
        self._principal_resolver = principal_resolver
        self._event_bus = event_bus
        self._api_key_header = api_key_header
        self._api_key_query_param = api_key_query_param
        self._logger = get_logger("teaf.security")

    def _extract_credentials(self, request: Request) -> AuthenticationCredentials:
        """Traduce headers/query string HTTP a ``AuthenticationCredentials`` genéricas."""
        auth_header = request.headers.get("Authorization")
        if auth_header:
            scheme_part, _, value = auth_header.partition(" ")
            scheme_part = scheme_part.lower()
            if scheme_part == "bearer" and value:
                return AuthenticationCredentials(scheme=_sniff_bearer_scheme(value), token=value)
            if scheme_part == "basic" and value:
                username, password = _decode_basic_auth(value)
                return AuthenticationCredentials(
                    scheme="ldap", username=username, password=password
                )

        api_key = request.headers.get(self._api_key_header) or request.query_params.get(
            self._api_key_query_param
        )
        if api_key:
            return AuthenticationCredentials(scheme="api-key", api_key=api_key)

        return AuthenticationCredentials(scheme="anonymous")

    def _publish(self, name: str, payload: dict[str, object]) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(Event(name=name, payload=payload))

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        credentials = self._extract_credentials(request)
        self._publish("authentication.started", {"scheme": credentials.scheme})

        provider = self._registry.resolve(credentials)
        principal = ANONYMOUS_PRINCIPAL
        if provider is not None:
            try:
                result = await provider.authenticate(credentials)
                principal = self._principal_resolver.resolve(result.identity)
                self._publish(
                    "authentication.succeeded",
                    {"principalId": principal.id, "providerId": provider.provider_id},
                )
            except AuthenticationException as exc:
                self._logger.info(
                    "authentication_failed",
                    extra={"context": {"scheme": credentials.scheme, "reason": str(exc)}},
                )
                self._publish(
                    "authentication.failed",
                    {"scheme": credentials.scheme, "providerId": provider.provider_id},
                )

        context = build_security_context(
            principal,
            correlation_id=get_correlation_id(),
            request_id=get_correlation_id(),
        )
        set_security_context(context)

        return await call_next(request)
