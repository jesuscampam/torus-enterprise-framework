"""Excepciones de la plataforma de protección de APIs (Sprint 2.9, ADR-009).

Todas heredan de ``ApiProtectionException`` y, a través de ella, de
``ApplicationException`` (``core/exceptions.py``) — así el manejador
centralizado de ``middleware/exception_handler.py`` ya las traduce a RFC
7807 sin ningún cableado adicional, igual que cualquier otra excepción del
framework.

Cada una fija su propio ``http_status`` porque la jerarquía original de
``core/exceptions.py`` no cubre los códigos que exige la protección de APIs
(429 "Too Many Requests", 413 "Payload Too Large", 415 "Unsupported Media
Type", 409 "Conflict"). ``ApplicationException.http_status`` es el punto de
extensión declarativo que hace posible eso sin que ``middleware/`` tenga
que importar este archivo — ver la nota de diseño en
``middleware/exception_handler.py``.
"""

from __future__ import annotations

from teaf._internal.core.exceptions import ApplicationException


class ApiProtectionException(ApplicationException):
    """Base de todo rechazo emitido por la plataforma de protección de APIs."""

    default_error_code = "api-protection-error"
    http_status = 400


class RateLimitExceededException(ApiProtectionException):
    """Se superó una regla de rate limiting — HTTP 429.

    ``retry_after_seconds`` es lo que el middleware traduce a la cabecera
    ``Retry-After`` de la respuesta.
    """

    default_error_code = "rate-limit-exceeded"
    http_status = 429

    def __init__(
        self,
        message: str,
        *,
        rule: str = "",
        retry_after_seconds: float = 0.0,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code)
        self.rule = rule
        self.retry_after_seconds = retry_after_seconds


class QuotaExceededException(ApiProtectionException):
    """Se agotó una cuota (peticiones, ancho de banda o concurrencia) — HTTP 429."""

    default_error_code = "quota-exceeded"
    http_status = 429

    def __init__(
        self,
        message: str,
        *,
        rule: str = "",
        retry_after_seconds: float = 0.0,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, error_code=error_code)
        self.rule = rule
        self.retry_after_seconds = retry_after_seconds


class RequestTooLargeException(ApiProtectionException):
    """El cuerpo de la petición supera el máximo permitido — HTTP 413."""

    default_error_code = "request-too-large"
    http_status = 413


class ResponseTooLargeException(ApiProtectionException):
    """La respuesta generada supera el máximo permitido — HTTP 500.

    A diferencia del resto, esto no es un error del cliente: la petición era
    válida y fue el servidor quien produjo una respuesta fuera del contrato
    declarado, así que se trata como fallo interno (ver
    docs/api/API-PROTECTION.md).
    """

    default_error_code = "response-too-large"
    http_status = 500


class UnsupportedContentTypeException(ApiProtectionException):
    """El ``Content-Type`` de la petición no está en la lista permitida — HTTP 415."""

    default_error_code = "unsupported-content-type"
    http_status = 415


class InvalidRequestException(ApiProtectionException):
    """La petición incumple una regla de validación de borde — HTTP 400.

    Cubre cabeceras obligatorias ausentes, ``User-Agent`` bloqueado y URLs
    excesivamente largas: validaciones de forma que se resuelven antes de
    llegar al endpoint, distintas de las de payload que ya cubre Pydantic.
    """

    default_error_code = "invalid-request"
    http_status = 400


class UnsupportedApiVersionException(ApiProtectionException):
    """El cliente pidió una versión de API que no se sirve — HTTP 400."""

    default_error_code = "unsupported-api-version"
    http_status = 400

    def __init__(
        self, message: str, *, requested: str | None = None, error_code: str | None = None
    ) -> None:
        super().__init__(message, error_code=error_code)
        self.requested = requested


class IdempotencyConflictException(ApiProtectionException):
    """La ``Idempotency-Key`` se reutilizó con una petición distinta — HTTP 409."""

    default_error_code = "idempotency-conflict"
    http_status = 409
