"""``RequestValidator`` — validación de borde de peticiones y respuestas (Sprint 2.9).

Complementa, sin solaparse, la validación que ya hace FastAPI/Pydantic: esto
se evalúa **antes** de que la petición llegue al endpoint y sobre metadatos
(tamaño, tipo de contenido, cabeceras, agente de usuario, longitud de URL),
no sobre la forma del payload. La distinción importa por seguridad: rechazar
un cuerpo de 500 MB por su ``Content-Length`` cuesta microsegundos, mientras
que dejar que Pydantic intente parsearlo cuesta memoria y tiempo de CPU que
un atacante controla.

Cada comprobación lanza la excepción específica de
``api/exceptions.py`` — nunca un ``ValueError`` genérico — para que el
cliente reciba el código HTTP correcto (413, 415 o 400) y un cuerpo RFC 7807
coherente con el resto del framework.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from teaf._internal.api.exceptions import (
    InvalidRequestException,
    RequestTooLargeException,
    ResponseTooLargeException,
    UnsupportedContentTypeException,
)

#: Métodos que, por definición de HTTP, no llevan cuerpo — no se les exige
#: ``Content-Type`` aunque haya una lista de tipos permitidos.
_BODYLESS_METHODS = frozenset({"GET", "HEAD", "DELETE", "OPTIONS", "TRACE"})


@dataclass(frozen=True, slots=True)
class RequestValidationPolicy:
    """Límites de forma que toda petición debe respetar.

    Los valores por defecto son deliberadamente generosos (10 MB de cuerpo,
    sin restricción de tipo ni de agente): activar la validación no debe
    romper una aplicación existente — quien necesita apretar los límites los
    declara (ver docs/api/API-PROTECTION.md).
    """

    max_request_bytes: int = 10 * 1024 * 1024
    max_response_bytes: int = 50 * 1024 * 1024
    #: Vacío = cualquier tipo permitido. Se compara solo el tipo de medio,
    #: ignorando parámetros (``application/json; charset=utf-8`` encaja con
    #: ``application/json``).
    allowed_content_types: tuple[str, ...] = ()
    #: Cabeceras obligatorias en toda petición (comparación sin distinguir
    #: mayúsculas), p. ej. ``("X-Request-Id",)``.
    required_headers: tuple[str, ...] = ()
    #: Subcadenas que, si aparecen en el ``User-Agent``, provocan rechazo.
    blocked_user_agents: tuple[str, ...] = ()
    #: Si no está vacío, el ``User-Agent`` debe contener alguna de estas
    #: subcadenas — lista blanca, más estricta que ``blocked_user_agents``.
    allowed_user_agents: tuple[str, ...] = ()
    require_user_agent: bool = False
    max_url_length: int = 8_000

    @property
    def enabled(self) -> bool:
        """Siempre activa: incluso sin listas, los límites de tamaño aplican."""
        return True


def _media_type(content_type: str) -> str:
    """Tipo de medio sin parámetros, en minúsculas."""
    return content_type.split(";", 1)[0].strip().lower()


class RequestValidator:
    """Valida metadatos de petición y tamaño de respuesta contra una política."""

    def __init__(self, policy: RequestValidationPolicy | None = None) -> None:
        self._policy = policy or RequestValidationPolicy()

    @property
    def policy(self) -> RequestValidationPolicy:
        """Política aplicada por este validador."""
        return self._policy

    def validate_request(
        self,
        *,
        method: str = "GET",
        url: str = "/",
        headers: Mapping[str, str] | None = None,
        content_length: int | None = None,
    ) -> None:
        """Valida una petición entrante.

        Raises:
            RequestTooLargeException: el cuerpo supera ``max_request_bytes``.
            UnsupportedContentTypeException: el ``Content-Type`` no está permitido.
            InvalidRequestException: falta una cabecera obligatoria, la URL es
                demasiado larga o el ``User-Agent`` no se admite.
        """
        lowered = {name.lower(): value for name, value in (headers or {}).items()}

        if len(url) > self._policy.max_url_length:
            raise InvalidRequestException(
                f"La URL supera la longitud máxima permitida "
                f"({len(url)} > {self._policy.max_url_length} caracteres)."
            )

        declared = content_length
        if declared is None:
            raw = lowered.get("content-length")
            declared = int(raw) if raw is not None and raw.isdigit() else 0
        if declared > self._policy.max_request_bytes:
            raise RequestTooLargeException(
                f"El cuerpo de la petición supera el máximo permitido "
                f"({declared} > {self._policy.max_request_bytes} bytes)."
            )

        for header in self._policy.required_headers:
            if header.lower() not in lowered:
                raise InvalidRequestException(f"Falta la cabecera obligatoria '{header}'.")

        self._validate_content_type(method=method, headers=lowered, content_length=declared)
        self._validate_user_agent(lowered.get("user-agent"))

    def validate_response(self, *, content_length: int) -> None:
        """Valida el tamaño de una respuesta ya generada.

        Raises:
            ResponseTooLargeException: supera ``max_response_bytes``.
        """
        if content_length > self._policy.max_response_bytes:
            raise ResponseTooLargeException(
                f"La respuesta supera el máximo permitido "
                f"({content_length} > {self._policy.max_response_bytes} bytes)."
            )

    def _validate_content_type(
        self, *, method: str, headers: Mapping[str, str], content_length: int
    ) -> None:
        if not self._policy.allowed_content_types:
            return
        # Un método sin cuerpo, o un cuerpo vacío, no necesita declarar tipo.
        if method.upper() in _BODYLESS_METHODS or content_length == 0:
            return
        content_type = headers.get("content-type")
        if content_type is None:
            raise UnsupportedContentTypeException(
                "La petición debe declarar un 'Content-Type'. Tipos permitidos: "
                f"{', '.join(self._policy.allowed_content_types)}."
            )
        allowed = {_media_type(t) for t in self._policy.allowed_content_types}
        if _media_type(content_type) not in allowed:
            raise UnsupportedContentTypeException(
                f"El tipo de contenido '{_media_type(content_type)}' no está permitido. "
                f"Tipos permitidos: {', '.join(sorted(allowed))}."
            )

    def _validate_user_agent(self, user_agent: str | None) -> None:
        if not user_agent:
            if self._policy.require_user_agent:
                raise InvalidRequestException("La petición debe declarar un 'User-Agent'.")
            return
        lowered = user_agent.lower()
        if any(blocked.lower() in lowered for blocked in self._policy.blocked_user_agents):
            raise InvalidRequestException("El 'User-Agent' de la petición no está permitido.")
        if self._policy.allowed_user_agents and not any(
            allowed.lower() in lowered for allowed in self._policy.allowed_user_agents
        ):
            raise InvalidRequestException("El 'User-Agent' de la petición no está permitido.")
