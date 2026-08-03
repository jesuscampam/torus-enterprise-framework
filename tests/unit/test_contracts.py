"""Pruebas unitarias de backend/contracts/ — verifican que son interfaces puras."""

from __future__ import annotations

import pytest
from backend.contracts.ai import AIProvider
from backend.contracts.capability_provider import CapabilityProvider
from backend.contracts.database import DatabaseProvider
from backend.contracts.framework_knowledge import FrameworkKnowledgeProvider
from backend.contracts.notification import NotificationChannel, NotificationProvider
from backend.contracts.repository import Repository
from backend.contracts.scheduler import SchedulerProvider
from backend.contracts.security import AuthenticationProvider, AuthorizationProvider
from backend.contracts.storage import StorageProvider
from backend.contracts.telemetry import TelemetryProvider
from backend.contracts.unit_of_work import UnitOfWork

_ALL_CONTRACTS: tuple[type, ...] = (
    Repository,
    UnitOfWork,
    DatabaseProvider,
    AuthenticationProvider,
    AuthorizationProvider,
    TelemetryProvider,
    StorageProvider,
    AIProvider,
    SchedulerProvider,
    NotificationProvider,
    CapabilityProvider,
    FrameworkKnowledgeProvider,
)


@pytest.mark.parametrize("contract", _ALL_CONTRACTS)
def test_contract_cannot_be_instantiated_directly(contract: type) -> None:
    """Ningún contrato tiene lógica propia: instanciarlo debe fallar por métodos abstractos."""
    with pytest.raises(TypeError):
        contract()


def test_repository_minimal_implementation_is_instantiable() -> None:
    class InMemoryRepository(Repository[dict[str, object]]):
        async def get_by_id(self, entity_id):  # type: ignore[no-untyped-def]
            return None

        async def list_paginated(self, *, page, page_size):  # type: ignore[no-untyped-def]
            return []

        async def add(self, entity):  # type: ignore[no-untyped-def]
            return entity

        async def update(self, entity):  # type: ignore[no-untyped-def]
            return entity

        async def delete(self, entity_id):  # type: ignore[no-untyped-def]
            return None

    repository = InMemoryRepository()
    assert isinstance(repository, Repository)


def test_notification_channel_values() -> None:
    assert NotificationChannel.EMAIL.value == "email"
    assert NotificationChannel.PUSH.value == "push"
    assert NotificationChannel.CHAT.value == "chat"


def test_capability_provider_minimal_implementation_is_instantiable() -> None:
    class StaticCapabilityProvider(CapabilityProvider):
        def get_capabilities(self) -> list[object]:
            return []

    provider = StaticCapabilityProvider()
    assert isinstance(provider, CapabilityProvider)
    assert provider.get_capabilities() == []


def test_framework_knowledge_provider_minimal_implementation_is_instantiable() -> None:
    class StaticFrameworkKnowledgeProvider(FrameworkKnowledgeProvider):
        async def describe_framework(self) -> dict[str, object]:
            return {"framework": "TEAF"}

        async def answer_question(self, question: str) -> str:
            return f"no sé responder a: {question}"

    provider = StaticFrameworkKnowledgeProvider()
    assert isinstance(provider, FrameworkKnowledgeProvider)
