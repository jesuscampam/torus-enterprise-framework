"""Utilidades genéricas sobre colecciones. Sin lógica de negocio."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def chunk(items: Iterable[T], size: int) -> Iterator[list[T]]:
    """Divide ``items`` en listas de tamaño ``size`` (la última puede ser más corta)."""
    if size <= 0:
        raise ValueError("size debe ser mayor que 0")
    iterator = iter(items)
    while batch := list(islice(iterator, size)):
        yield batch


def flatten(nested: Iterable[Iterable[T]]) -> list[T]:
    """Aplana un iterable de iterables en una única lista, un nivel de profundidad."""
    return [item for sublist in nested for item in sublist]
