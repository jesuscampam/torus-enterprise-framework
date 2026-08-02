"""Utilidad compartida para invocar hooks síncronos o asíncronos.

Usada por ``lifecycle.py`` y ``pipeline.py`` — ambos permiten registrar
funciones normales o corutinas indistintamente, igual que el ``lifespan``
de FastAPI/Starlette.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

#: Un hook no recibe argumentos y su valor de retorno se ignora — puede ser
#: una función síncrona o una corutina.
Hook = Callable[[], Any]


async def invoke_hook(hook: Hook) -> None:
    """Ejecuta ``hook``, esperando su resultado si es una corutina."""
    result = hook()
    if inspect.isawaitable(result):
        await result
