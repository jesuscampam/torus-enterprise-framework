"""Pruebas unitarias de backend/core/dependencies.py (singleton_provider)."""

from __future__ import annotations

from teaf._internal.core.dependencies import singleton_provider


def test_singleton_provider_caches_single_instance() -> None:
    calls: list[int] = []

    @singleton_provider
    def factory() -> object:
        calls.append(1)
        return object()

    first = factory()
    second = factory()

    assert first is second
    assert len(calls) == 1


def test_singleton_provider_is_independent_per_decorated_function() -> None:
    @singleton_provider
    def factory_a() -> str:
        return "a"

    @singleton_provider
    def factory_b() -> str:
        return "b"

    assert factory_a() == "a"
    assert factory_b() == "b"
