"""Pruebas unitarias de backend/providers/ — factories y clases base."""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.contracts.database import DatabaseProvider
from teaf._internal.providers.database.connection_manager import ConnectionManager
from teaf._internal.providers.database.factory import DatabaseFactory
from teaf._internal.providers.security.factory import SecurityFactory
from teaf._internal.providers.security.rbac import Role
from teaf._internal.providers.security.security_context import (
    ANONYMOUS,
    SecurityContext,
    get_security_context,
    set_security_context,
)
from teaf._internal.providers.telemetry.telemetry_context import get_telemetry_context


def test_database_factory_is_abstract() -> None:
    with pytest.raises(TypeError):
        DatabaseFactory()  # type: ignore[abstract]


def test_security_factory_is_abstract() -> None:
    with pytest.raises(TypeError):
        SecurityFactory()  # type: ignore[abstract]


def test_connection_manager_tracks_connection_state() -> None:
    class FakeConnectionManager(ConnectionManager):
        async def connect(self) -> None:
            self._mark_connected()

        async def disconnect(self) -> None:
            self._mark_disconnected()

        def get_session(self) -> object:
            raise NotImplementedError

        async def health_check(self) -> bool:
            return self.is_connected

    manager = FakeConnectionManager()
    assert isinstance(manager, DatabaseProvider)
    assert manager.is_connected is False

    asyncio.run(manager.connect())
    assert manager.is_connected is True

    asyncio.run(manager.disconnect())
    assert manager.is_connected is False


def test_security_context_default_is_anonymous() -> None:
    context = get_security_context()
    assert context == ANONYMOUS
    assert context.is_authenticated is False


def test_security_context_has_permission() -> None:
    role = Role(name="editor", permissions=frozenset({"incidents:write"}))
    context = SecurityContext(principal_id="user-1", roles=frozenset({role}))

    assert context.is_authenticated is True
    assert context.has_permission("incidents:write") is True
    assert context.has_permission("incidents:delete") is False


def test_telemetry_context_default_has_no_active_trace() -> None:
    context = get_telemetry_context()
    assert context.trace_id is None
    assert context.span_id is None


def test_set_security_context_propagates_identity_to_core_context() -> None:
    """Sprint 2.8 (ADR-008): ``JsonFormatter`` lee ``userId``/``tenant`` de
    ``core/context.py``, no de ``SecurityContext`` — ``set_security_context``
    debe seguir propagando ambos para que el logging estructurado los vea."""
    from teaf._internal.core.context import get_tenant_id, get_user_id, set_identity_context

    context = SecurityContext(principal_id="user-42", tenant_id="tenant-9")
    set_security_context(context)

    assert get_user_id() == "user-42"
    assert get_tenant_id() == "tenant-9"

    # Aislamiento entre pruebas.
    set_security_context(ANONYMOUS)
    set_identity_context(user_id=None, tenant_id=None)
