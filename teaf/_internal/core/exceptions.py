"""Jerarquía de excepciones base del framework.

Toda excepción de negocio o de infraestructura en TEAF hereda de
``ApplicationException`` (ver docs/architecture/FRAMEWORK-BLUEPRINT.md,
sección 9 y 11 — "toda excepción de negocio hereda de una excepción base
definida en core/"). Los manejadores de ``backend/middleware/`` capturan
esta jerarquía y la traducen a respuestas RFC 7807 (ver
docs/standards/API-STANDARD.md, sección 6).
"""

from __future__ import annotations


class ApplicationException(Exception):
    """Excepción base de la que heredan todas las excepciones de TEAF.

    Args:
        message: Descripción legible del error, segura para exponer al
            cliente (nunca debe contener detalles internos sensibles).
        error_code: Identificador corto y estable del tipo de error,
            usado para construir el campo ``type`` de la respuesta RFC 7807.
    """

    #: Código de error por defecto; las subclases lo sobrescriben.
    default_error_code: str = "application-error"

    def __init__(self, message: str, *, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.default_error_code


class BusinessException(ApplicationException):
    """Se viola una regla de negocio (capa Application/Domain).

    Ejemplo futuro: intentar transicionar un recurso a un estado no
    permitido por sus reglas de dominio.
    """

    default_error_code = "business-error"


class ValidationException(ApplicationException):
    """Los datos de entrada no cumplen una regla de validación.

    Se distingue de los errores de validación de forma que ya resuelve
    FastAPI/Pydantic en el borde de la API: esta excepción es para
    validaciones que dependen de estado o de reglas de negocio, no de
    la forma del payload.
    """

    default_error_code = "validation-error"


class InfrastructureException(ApplicationException):
    """Falla un componente de infraestructura (base de datos, red, IO).

    No debe exponer detalles técnicos internos en ``message``; el detalle
    completo se registra en el log correlacionado, nunca en la respuesta.
    """

    default_error_code = "infrastructure-error"


class ConfigurationException(ApplicationException):
    """La configuración del framework es inválida o está incompleta.

    Se lanza durante el arranque (ver backend/config/environment.py y
    backend/config/settings.py) cuando falta una variable de entorno
    requerida o su valor no es válido para el entorno detectado.
    """

    default_error_code = "configuration-error"


class AuthenticationException(ApplicationException):
    """Placeholder: el llamante no está autenticado o el token es inválido.

    Sin implementación funcional en Sprint 2.1 — el módulo `security/`
    (Sprint 2.2) es responsable de lanzarla; aquí solo se fija el contrato
    de la jerarquía para que `middleware/exception_handler.py` ya sepa
    traducirla a HTTP 401 en cuanto exista.
    """

    default_error_code = "authentication-error"


class AuthorizationException(ApplicationException):
    """Placeholder: el llamante está autenticado pero no autorizado.

    Sin implementación funcional en Sprint 2.1 — mismo motivo que
    ``AuthenticationException``. Se traduce a HTTP 403.
    """

    default_error_code = "authorization-error"
