"""Infraestructura mínima de Dependency Injection para FastAPI.

TEAF utiliza el sistema nativo de FastAPI (``Depends()``) como mecanismo de
inyección de dependencias — no se introduce un contenedor de DI de terceros
(ver FRAMEWORK-BLUEPRINT.md, sección 12: "no implementar contenedores
complejos"). Este módulo solo provee la utilidad genérica para declarar
*providers* (funciones factory) que FastAPI resuelve como singletons de
proceso, siguiendo el patrón estándar de ``functools.lru_cache`` documentado
en la propia guía de FastAPI.

Ejemplo de uso futuro (Sprint 2.2+), sin implementarlo aquí:

    @singleton_provider
    def get_db_session_factory() -> SessionFactory: ...

    # En un router:
    def endpoint(session=Depends(get_db_session_factory)): ...
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from typing import TypeVar

T = TypeVar("T")


def singleton_provider(factory: Callable[[], T]) -> Callable[[], T]:
    """Envuelve una factory sin argumentos para que FastAPI la resuelva una única vez por proceso.

    Cualquier módulo del framework que necesite exponer una dependencia
    inyectable de ciclo de vida "singleton" (una única instancia por
    proceso, p. ej. la configuración resuelta) debe declarar su factory con
    este decorador en vez de instanciar el objeto a nivel de módulo.
    """
    return lru_cache(maxsize=1)(factory)
