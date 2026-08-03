"""Pruebas unitarias de backend/runtime/service_discovery.py (ServiceDiscovery)."""

from __future__ import annotations

import pytest
from backend.runtime.container import Lifetime, ServiceContainer, ServiceMetadata
from backend.runtime.exceptions import ServiceNotRegisteredException
from backend.runtime.service_discovery import ServiceDiscovery


class _Greeter:
    pass


class _OtherGreeter:
    pass


def test_list_returns_all_registered_services() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())
    discovery = ServiceDiscovery(container)

    assert len(discovery.list()) == 1
    assert discovery.list()[0].service_id == "_Greeter"


def test_search_matches_service_id_name_and_tags() -> None:
    container = ServiceContainer()
    metadata = ServiceMetadata(
        service_id="greeter", name="Greeter", lifetime=Lifetime.SINGLETON, tags=("demo",)
    )
    container.register_singleton(_Greeter, lambda _c: _Greeter(), metadata=metadata)
    discovery = ServiceDiscovery(container)

    assert discovery.search("greet") == (metadata,)
    assert discovery.search("demo") == (metadata,)
    assert discovery.search("does-not-match") == ()


def test_resolve_delegates_to_container() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())
    discovery = ServiceDiscovery(container)

    assert isinstance(discovery.resolve(_Greeter), _Greeter)


def test_resolve_unregistered_contract_raises() -> None:
    discovery = ServiceDiscovery(ServiceContainer())
    with pytest.raises(ServiceNotRegisteredException):
        discovery.resolve(_Greeter)


def test_describe_returns_metadata_by_service_id() -> None:
    container = ServiceContainer()
    container.register_singleton(_Greeter, lambda _c: _Greeter())
    discovery = ServiceDiscovery(container)

    assert discovery.describe("_Greeter").service_id == "_Greeter"


def test_describe_unknown_service_id_raises() -> None:
    discovery = ServiceDiscovery(ServiceContainer())
    with pytest.raises(ServiceNotRegisteredException):
        discovery.describe("does-not-exist")


def test_capabilities_returns_declared_capabilities() -> None:
    container = ServiceContainer()
    metadata = ServiceMetadata(
        service_id="greeter",
        name="Greeter",
        lifetime=Lifetime.SINGLETON,
        capabilities=("greet.hello",),
    )
    container.register_singleton(_Greeter, lambda _c: _Greeter(), metadata=metadata)
    discovery = ServiceDiscovery(container)

    assert discovery.capabilities("greeter") == ("greet.hello",)


def test_dependency_tree_expands_registered_dependencies() -> None:
    container = ServiceContainer()
    other_metadata = ServiceMetadata(service_id="other", name="Other", lifetime=Lifetime.SINGLETON)
    greeter_metadata = ServiceMetadata(
        service_id="greeter",
        name="Greeter",
        lifetime=Lifetime.SINGLETON,
        dependencies=("other", "unregistered"),
    )
    container.register_singleton(_OtherGreeter, lambda _c: _OtherGreeter(), metadata=other_metadata)
    container.register_singleton(_Greeter, lambda _c: _Greeter(), metadata=greeter_metadata)
    discovery = ServiceDiscovery(container)

    tree = discovery.dependency_tree("greeter")

    assert tree == {
        "id": "greeter",
        "dependencies": [
            {"id": "other", "dependencies": []},
            {"id": "unregistered", "dependencies": []},
        ],
    }


def test_dependency_tree_protects_against_cycles() -> None:
    container = ServiceContainer()
    a_metadata = ServiceMetadata(
        service_id="a", name="A", lifetime=Lifetime.SINGLETON, dependencies=("b",)
    )
    b_metadata = ServiceMetadata(
        service_id="b", name="B", lifetime=Lifetime.SINGLETON, dependencies=("a",)
    )

    class _A:
        pass

    class _B:
        pass

    container.register_singleton(_A, lambda _c: _A(), metadata=a_metadata)
    container.register_singleton(_B, lambda _c: _B(), metadata=b_metadata)
    discovery = ServiceDiscovery(container)

    tree = discovery.dependency_tree("a")  # no debe recursar infinitamente

    assert tree["id"] == "a"
    assert tree["dependencies"][0]["id"] == "b"  # type: ignore[index]


def test_dependency_tree_unknown_service_id_raises() -> None:
    discovery = ServiceDiscovery(ServiceContainer())
    with pytest.raises(ServiceNotRegisteredException):
        discovery.dependency_tree("does-not-exist")
