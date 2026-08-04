"""Pruebas unitarias de backend/runtime/container.py (ServiceContainer)."""

from __future__ import annotations

import pytest
from teaf._internal.runtime.container import (
    Lifetime,
    ServiceContainer,
    ServiceHealth,
    ServiceMetadata,
)
from teaf._internal.runtime.exceptions import (
    CircularDependencyException,
    ServiceNotRegisteredException,
)


class _Greeter:
    def __init__(self, message: str = "hola") -> None:
        self.message = message


class _OtherGreeter:
    pass


def test_resolve_unregistered_contract_raises() -> None:
    container = ServiceContainer()
    with pytest.raises(ServiceNotRegisteredException):
        container.resolve(_Greeter)


def test_is_registered_reflects_registration_state() -> None:
    container = ServiceContainer()
    assert container.is_registered(_Greeter) is False

    container.register_transient(_Greeter, lambda _c: _Greeter())
    assert container.is_registered(_Greeter) is True


def test_singleton_returns_same_instance_across_resolves() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())

    first = container.resolve(_Greeter)
    second = container.resolve(_Greeter)

    assert first is second


def test_transient_returns_new_instance_each_time() -> None:
    container = ServiceContainer()
    container.register_transient(_Greeter, lambda _c: _Greeter())

    first = container.resolve(_Greeter)
    second = container.resolve(_Greeter)

    assert first is not second


def test_singleton_factory_is_lazy_until_first_resolve() -> None:
    calls: list[int] = []

    def factory(_container: ServiceContainer) -> _Greeter:
        calls.append(1)
        return _Greeter()

    container = ServiceContainer()
    container.register_singleton(_Greeter, factory)

    assert calls == []
    container.resolve(_Greeter)
    assert calls == [1]
    container.resolve(_Greeter)
    assert calls == [1]  # no se vuelve a invocar la factory


def test_register_instance_is_returned_as_is() -> None:
    container = ServiceContainer()
    instance = _Greeter(message="ya construido")

    container.register_instance(_Greeter, instance)

    assert container.resolve(_Greeter) is instance


def test_scoped_without_scope_raises() -> None:
    container = ServiceContainer()
    container.register_scoped(_Greeter, lambda _c: _Greeter())

    with pytest.raises(ServiceNotRegisteredException):
        container.resolve(_Greeter)


def test_scoped_shares_instance_within_scope_only() -> None:
    container = ServiceContainer()
    container.register_scoped(_Greeter, lambda _c: _Greeter())

    with container.create_scope() as scope_a:
        first = scope_a.resolve(_Greeter)
        second = scope_a.resolve(_Greeter)
        assert first is second

    with container.create_scope() as scope_b:
        third = scope_b.resolve(_Greeter)
        assert third is not first


def test_scope_clears_instances_on_exit() -> None:
    container = ServiceContainer()
    container.register_scoped(_Greeter, lambda _c: _Greeter())

    with container.create_scope() as scope:
        scope.resolve(_Greeter)
        assert len(scope._instances) == 1

    assert len(scope._instances) == 0


def test_factory_can_resolve_other_registered_dependencies() -> None:
    container = ServiceContainer()
    container.register_singleton(_OtherGreeter, lambda _c: _OtherGreeter())
    container.register_singleton(
        _Greeter, lambda c: _Greeter(message=str(type(c.resolve(_OtherGreeter)).__name__))
    )

    resolved = container.resolve(_Greeter)
    assert resolved.message == "_OtherGreeter"


def test_circular_dependency_is_detected() -> None:
    container = ServiceContainer()

    class A:
        pass

    class B:
        pass

    container.register_transient(A, lambda c: (c.resolve(B), A())[1])
    container.register_transient(B, lambda c: (c.resolve(A), B())[1])

    with pytest.raises(CircularDependencyException):
        container.resolve(A)


def test_registered_contracts_lists_everything_registered() -> None:
    container = ServiceContainer()
    container.register_transient(_Greeter, lambda _c: _Greeter())
    container.register_singleton(_OtherGreeter, lambda _c: _OtherGreeter())

    assert set(container.registered_contracts()) == {_Greeter, _OtherGreeter}


def test_resolve_lazy_defers_construction_until_value_access() -> None:
    calls: list[int] = []

    def factory(_container: ServiceContainer) -> _Greeter:
        calls.append(1)
        return _Greeter()

    container = ServiceContainer()
    container.register_transient(_Greeter, factory)

    lazy = container.resolve_lazy(_Greeter)
    assert calls == []
    assert lazy.is_resolved is False

    _ = lazy.value
    assert calls == [1]
    assert lazy.is_resolved is True

    _ = lazy.value
    assert calls == [1]  # cacheado tras el primer acceso


def test_lifetime_enum_values() -> None:
    assert Lifetime.SINGLETON.value == "singleton"
    assert Lifetime.SCOPED.value == "scoped"
    assert Lifetime.TRANSIENT.value == "transient"


def test_unregister_removes_provider_and_singleton_instance() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())
    container.resolve(_Greeter)

    container.unregister(_Greeter)

    assert container.is_registered(_Greeter) is False
    with pytest.raises(ServiceNotRegisteredException):
        container.resolve(_Greeter)


def test_unregister_unknown_contract_raises() -> None:
    container = ServiceContainer()
    with pytest.raises(ServiceNotRegisteredException):
        container.unregister(_Greeter)


def test_describe_services_synthesizes_metadata_when_none_given() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())

    described = container.describe_services()

    assert len(described) == 1
    assert described[0].service_id == "_Greeter"
    assert described[0].name == "_Greeter"
    assert described[0].lifetime is Lifetime.SINGLETON
    assert described[0].health is ServiceHealth.UNKNOWN


def test_describe_services_returns_explicit_metadata_when_given() -> None:
    container = ServiceContainer()
    metadata = ServiceMetadata(
        service_id="greeter",
        name="Greeter",
        lifetime=Lifetime.TRANSIENT,
        module="demo",
        dependencies=("other",),
        capabilities=("demo.cap",),
        health=ServiceHealth.HEALTHY,
        tags=("demo",),
    )
    container.register_transient(_Greeter, lambda _c: _Greeter(), metadata=metadata)

    described = container.describe_services()

    assert described == (metadata,)
    assert described[0].as_dict()["serviceId"] == "greeter"
    assert described[0].as_dict()["health"] == "healthy"
