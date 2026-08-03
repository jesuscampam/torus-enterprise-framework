"""Prueba de integración: DatabaseModule contra un Runtime real de extremo a extremo.

Es la prueba arquitectónica central del Sprint 2.6: demuestra que un módulo
construido enteramente sobre el Module SDK (Sprint 2.5) se registra, arranca
y opera contra el Runtime real (Sprint 2.3/2.4) sin una sola llamada directa
a ``ServiceContainer``/``CapabilityRegistry`` desde ``DatabaseModule`` —
todo pasa por ``ModuleBase.bootstrap()``, ``ServiceBinder`` y
``CapabilityBinder``.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import cast

from backend.contracts.database import DatabaseProvider
from backend.contracts.unit_of_work import UnitOfWork
from backend.core.registry import ModuleRegistry
from backend.modules.database.module import DatabaseModule
from backend.providers.database.base_model import AuditMixin, Base
from backend.providers.database.sqlalchemy_repository import SQLAlchemyRepository
from backend.providers.database.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from backend.runtime.capabilities.enums import CapabilityHealth
from backend.runtime.runtime import Runtime
from backend.sdk.context import ModuleContext
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class _Account(Base, AuditMixin):
    __tablename__ = "_test_bootstrap_account"
    name: Mapped[str] = mapped_column(String(50))


def _running_runtime() -> Runtime:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.5.0-alpha")
    asyncio.run(runtime.startup())
    return runtime


def test_bootstrap_registers_module_in_core_registry() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    asyncio.run(module.bootstrap(context))

    names = {descriptor.name for descriptor in runtime.modules}
    assert "database" in names


def test_bootstrap_registers_all_six_capabilities() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    asyncio.run(module.bootstrap(context))

    for capability_id in (
        "database",
        "database.connection",
        "database.repository",
        "database.transactions",
        "database.migration",
        "database.health",
    ):
        assert runtime.capability_registry.exists(capability_id) is True


def test_bootstrap_registers_all_three_services_resolvable() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    asyncio.run(module.bootstrap(context))

    assert runtime.container.is_registered(DatabaseProvider) is True
    assert runtime.container.is_registered(UnitOfWork) is True

    provider = runtime.resolve_service(DatabaseProvider)
    assert provider is module.provider


def test_unit_of_work_service_is_transient_per_resolution() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    asyncio.run(module.bootstrap(context))

    first = runtime.resolve_service(UnitOfWork)
    second = runtime.resolve_service(UnitOfWork)
    assert first is not second


def test_full_repository_crud_through_resolved_unit_of_work() -> None:
    runtime = Runtime(registry=ModuleRegistry(), framework_version="0.5.0-alpha")
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    async def scenario() -> int:
        await runtime.startup()
        await module.bootstrap(context)

        # ``module._engine`` es el mismo motor que ``module.provider`` envuelve
        # (construidos juntos en ``DatabaseModule.__init__``) — se usa aquí
        # solo para preparar el esquema de la prueba, nunca en código de módulo.
        async with module._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

        uow = cast(SQLAlchemyUnitOfWork, runtime.resolve_service(UnitOfWork))
        async with uow:
            repo = SQLAlchemyRepository(uow.session, _Account)
            await repo.add(_Account(id=uuid.uuid4(), name="acme"))
            await uow.commit()

        uow = cast(SQLAlchemyUnitOfWork, runtime.resolve_service(UnitOfWork))
        async with uow:
            repo = SQLAlchemyRepository(uow.session, _Account)
            return await repo.count()

    assert asyncio.run(scenario()) == 1


def test_start_hook_makes_health_check_reflect_real_connectivity() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    asyncio.run(module.bootstrap(context))

    assert module.health.check() is CapabilityHealth.HEALTHY


def test_shutdown_disconnects_the_provider() -> None:
    runtime = _running_runtime()
    module = DatabaseModule()
    context = ModuleContext(runtime=runtime, module_id="database")

    async def scenario() -> None:
        await module.bootstrap(context)
        await module.shutdown(context)

    asyncio.run(scenario())
    assert module.provider.is_connected is False
