"""``@authorize()``/``@allow_anonymous()`` — autorización declarativa por endpoint.

``SecurityMiddleware`` nunca bloquea una petición por falta de autenticación
(ver ``middleware.py``) — la aplicación de la política es responsabilidad de
estos decoradores, aplicados sobre el handler de cada endpoint. Ambos
funcionan sobre el ``SecurityContext`` que el middleware ya publicó en el
``ContextVar`` de la petición en curso (``get_security_context()``), así que
no necesitan recibir ``Request``/``Depends`` — pueden envolver directamente
la función del endpoint.

``functools.wraps`` preserva ``__wrapped__``, y ``inspect.signature()``
(usado por FastAPI para construir el árbol de dependencias de cada ruta) lo
sigue automáticamente — el endpoint decorado conserva sus parámetros/
``Depends()`` originales de cara a FastAPI.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, TypeVar, cast

from teaf._internal.core.exceptions import AuthenticationException
from teaf._internal.providers.security.security_context import get_security_context
from teaf._internal.security.exceptions import (
    InsufficientPermissionException,
    PolicyViolationException,
)
from teaf._internal.security.models import ANONYMOUS_PRINCIPAL, Policy

F = TypeVar("F", bound=Callable[..., Any])


def _as_tuple(value: str | Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _check_access(
    roles: tuple[str, ...], permissions: tuple[str, ...], policy: Policy | None
) -> None:
    context = get_security_context()
    if not context.is_authenticated:
        raise AuthenticationException("Se requiere autenticación para acceder a este recurso.")

    if roles and not any(role.name in roles for role in context.roles):
        raise InsufficientPermissionException(
            f"Se requiere alguno de los roles: {', '.join(roles)}."
        )

    if permissions and not any(context.has_permission(permission) for permission in permissions):
        raise InsufficientPermissionException(
            f"Se requiere alguno de los permisos: {', '.join(permissions)}."
        )

    if policy is not None:
        principal = context.principal or ANONYMOUS_PRINCIPAL
        if not policy.evaluate(principal):
            raise PolicyViolationException(f"No se satisface la política '{policy.name}'.")


def authorize(
    *,
    role: str | Iterable[str] | None = None,
    permission: str | Iterable[str] | None = None,
    policy: Policy | None = None,
) -> Callable[[F], F]:
    """Exige autenticación y, opcionalmente, un rol/permiso/política sobre el endpoint decorado.

    ``@authorize()`` sin argumentos solo exige que la petición esté
    autenticada. ``role``/``permission`` aceptan un único nombre o varios
    (``Iterable[str]``) — basta con satisfacer uno de ellos (OR, no AND).
    Lanza ``AuthenticationException``/``InsufficientPermissionException``/
    ``PolicyViolationException`` (401/403 automáticos, ver
    ``teaf._internal.middleware.exception_handler``).
    """
    roles = _as_tuple(role)
    permissions = _as_tuple(permission)

    def decorator(func: F) -> F:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                _check_access(roles, permissions, policy)
                return await cast(Callable[..., Awaitable[Any]], func)(*args, **kwargs)

            return cast(F, async_wrapper)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            _check_access(roles, permissions, policy)
            return func(*args, **kwargs)

        return cast(F, sync_wrapper)

    return decorator


def allow_anonymous() -> Callable[[F], F]:
    """Marca declarativamente un endpoint como accesible sin autenticación.

    No-op en tiempo de ejecución — ``SecurityMiddleware`` ya deja pasar toda
    petición no autenticada como principal anónimo, y ningún endpoint sin
    ``@authorize()`` exige autenticación por defecto. Este decorador existe
    para dejar la intención explícita en el código (documentación ejecutable:
    "sí, este endpoint es público a propósito") y como punto de extensión si
    una aplicación futura decide invertir la política por defecto a
    "autenticación requerida salvo opt-out".
    """

    def decorator(func: F) -> F:
        func.__teaf_allow_anonymous__ = True  # type: ignore[attr-defined]
        return func

    return decorator
