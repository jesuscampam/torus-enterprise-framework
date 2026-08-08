"""``ApiVersionNegotiator`` — resuelve qué versión de API sirve cada petición (Sprint 2.9).

Soporta las tres formas habituales de declarar versión, en el orden de
prioridad configurado en ``ApiVersioningPolicy.strategies``:

1. **URI** — ``/api/v2/orders``: la más visible y la más fácil de enrutar en
   un balanceador o un gateway, a costa de ensuciar la URL del recurso.
2. **Cabecera** — ``X-API-Version: 2``: mantiene la URL limpia y es trivial
   de fijar en un cliente, pero es invisible en un navegador.
3. **Tipo de medio** — ``Accept: application/vnd.teaf.v2+json``: la más
   fiel a HTTP y la que mejor convive con la negociación de contenido, y
   también la más incómoda de escribir a mano.

Ninguna es "la correcta": TEAF implementa las tres y deja la elección —o la
combinación— a cada aplicación, que es justo lo que un framework debe hacer
(ver docs/api/VERSIONING.md).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field

from teaf._internal.api.exceptions import UnsupportedApiVersionException
from teaf._internal.api.models import ApiVersion, VersioningStrategy, VersionNegotiation

#: ``/api/v2/orders`` o ``/v2.1/orders`` — la versión debe ser un segmento
#: completo de la ruta, nunca una subcadena de un identificador.
_URI_VERSION_PATTERN = re.compile(r"(?:^|/)v(\d+(?:\.\d+)?)(?:/|$)")

#: ``application/vnd.teaf.v2+json`` — el proveedor (``teaf``) es
#: configurable; lo que se busca siempre es el token ``v<versión>``.
_MEDIA_TYPE_PATTERN_TEMPLATE = r"application/vnd\.{vendor}\.v(\d+(?:\.\d+)?)\+"


@dataclass(frozen=True, slots=True)
class ApiVersioningPolicy:
    """Qué versiones se sirven, cómo se piden y cuáles están en retirada.

    ``deprecated`` mapea versión → fecha/mensaje de retirada (*sunset*); esa
    información viaja al cliente en las cabeceras ``Deprecation`` y
    ``Sunset``, que es la forma estándar de avisar de una retirada sin
    romper a nadie todavía.
    """

    supported: tuple[ApiVersion, ...] = (ApiVersion(1),)
    default: ApiVersion = ApiVersion(1)
    strategies: tuple[VersioningStrategy, ...] = (
        VersioningStrategy.URI,
        VersioningStrategy.HEADER,
        VersioningStrategy.MEDIA_TYPE,
    )
    header_name: str = "X-API-Version"
    media_type_vendor: str = "teaf"
    deprecated: Mapping[str, str] = field(default_factory=dict)
    #: ``True`` rechaza (HTTP 400) una versión desconocida; ``False`` cae a
    #: ``default`` silenciosamente. Rechazar es el valor por defecto porque
    #: servir la v1 a quien pidió la v3 produce errores mucho más difíciles
    #: de diagnosticar que un 400 explícito.
    strict: bool = True

    @property
    def enabled(self) -> bool:
        """``True`` si hay alguna estrategia de negociación activa."""
        return bool(self.strategies)

    def is_supported(self, version: ApiVersion) -> bool:
        """``True`` si ``version`` está entre las servidas."""
        return version in self.supported

    def sunset_of(self, version: ApiVersion) -> str | None:
        """Mensaje/fecha de retirada de ``version``, o ``None`` si no está obsoleta."""
        return self.deprecated.get(str(version))


class ApiVersionNegotiator:
    """Traduce ruta y cabeceras de una petición a una ``VersionNegotiation``."""

    def __init__(self, policy: ApiVersioningPolicy | None = None) -> None:
        self._policy = policy or ApiVersioningPolicy()
        self._media_type_pattern = re.compile(
            _MEDIA_TYPE_PATTERN_TEMPLATE.format(vendor=re.escape(self._policy.media_type_vendor))
        )

    @property
    def policy(self) -> ApiVersioningPolicy:
        """Política aplicada por este negociador."""
        return self._policy

    def negotiate(
        self, *, path: str = "/", headers: Mapping[str, str] | None = None
    ) -> VersionNegotiation:
        """Resuelve la versión de la petición.

        Raises:
            UnsupportedApiVersionException: si el cliente pidió una versión
                inválida o no servida y la política es ``strict``.
        """
        headers = headers or {}
        requested, strategy = self._extract(path=path, headers=headers)

        if requested is None:
            return self._negotiation(
                self._policy.default, strategy=None, requested=None, default=True
            )

        try:
            version = ApiVersion.parse(requested)
        except ValueError as exc:
            if self._policy.strict:
                raise UnsupportedApiVersionException(
                    f"La versión de API solicitada no es válida: {requested!r}.",
                    requested=requested,
                ) from exc
            return self._negotiation(
                self._policy.default, strategy=strategy, requested=requested, default=True
            )

        if not self._policy.is_supported(version):
            if self._policy.strict:
                supported = ", ".join(str(v) for v in self._policy.supported)
                raise UnsupportedApiVersionException(
                    f"La versión de API {requested!r} no está soportada. "
                    f"Versiones disponibles: {supported}.",
                    requested=requested,
                )
            return self._negotiation(
                self._policy.default, strategy=strategy, requested=requested, default=True
            )

        return self._negotiation(version, strategy=strategy, requested=requested, default=False)

    def _negotiation(
        self,
        version: ApiVersion,
        *,
        strategy: VersioningStrategy | None,
        requested: str | None,
        default: bool,
    ) -> VersionNegotiation:
        sunset = self._policy.sunset_of(version)
        return VersionNegotiation(
            version=version,
            strategy=strategy,
            requested=requested,
            is_default=default,
            deprecated=sunset is not None,
            sunset=sunset,
        )

    def _extract(
        self, *, path: str, headers: Mapping[str, str]
    ) -> tuple[str | None, VersioningStrategy | None]:
        """Primera versión encontrada según el orden de ``policy.strategies``."""
        lowered = {name.lower(): value for name, value in headers.items()}
        for strategy in self._policy.strategies:
            if strategy is VersioningStrategy.URI:
                match = _URI_VERSION_PATTERN.search(path)
                if match:
                    return match.group(1), strategy
            elif strategy is VersioningStrategy.HEADER:
                value = lowered.get(self._policy.header_name.lower())
                if value:
                    return value.strip(), strategy
            elif strategy is VersioningStrategy.MEDIA_TYPE:
                match = self._media_type_pattern.search(lowered.get("accept", ""))
                if match:
                    return match.group(1), strategy
        return None, None

    def response_headers(self, negotiation: VersionNegotiation) -> dict[str, str]:
        """Cabeceras que informan al cliente de la versión servida y de su retirada."""
        headers = {"X-API-Version": str(negotiation.version)}
        if negotiation.deprecated:
            # "Deprecation: true" y "Sunset: <fecha>" son las cabeceras
            # estándar de retirada (RFC 8594 y su borrador complementario).
            headers["Deprecation"] = "true"
            if negotiation.sunset:
                headers["Sunset"] = negotiation.sunset
        return headers
