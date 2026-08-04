"""Pruebas unitarias de backend/modules/database/manifest.py (build_database_manifest)."""

from __future__ import annotations

from teaf._internal.contracts.database import DatabaseProvider
from teaf._internal.contracts.unit_of_work import UnitOfWork
from teaf._internal.modules.database.configuration import DatabaseConfiguration
from teaf._internal.modules.database.health import DatabaseHealth
from teaf._internal.modules.database.installer import DatabaseInstaller
from teaf._internal.modules.database.manifest import build_database_manifest
from teaf._internal.providers.database.engine import create_engine
from teaf._internal.providers.database.sqlalchemy_factory import SQLAlchemyDatabaseFactory
from teaf._internal.providers.database.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWorkFactory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.sdk.manifest import ModuleManifest


def _build_manifest(configuration: DatabaseConfiguration | None = None) -> ModuleManifest:
    config = configuration or DatabaseConfiguration()
    engine = create_engine(config.dialect, config.connection_parameters)
    factory = SQLAlchemyDatabaseFactory(engine)
    provider = factory.create()
    uow_factory = SQLAlchemyUnitOfWorkFactory(provider)  # type: ignore[arg-type]
    health = DatabaseHealth(provider)
    return build_database_manifest(
        config, provider=provider, uow_factory=uow_factory, health=health
    )


def test_descriptor_identifies_the_module() -> None:
    manifest = _build_manifest()
    assert manifest.descriptor.id == "database"
    assert manifest.descriptor.version == "1.0.0"
    assert manifest.license == "MIT"


def test_declares_the_six_required_capabilities() -> None:
    manifest = _build_manifest()
    ids = {capability.id for capability in manifest.capabilities}
    assert ids == {
        "database",
        "database.connection",
        "database.repository",
        "database.transactions",
        "database.migration",
        "database.health",
    }


def test_declares_the_three_required_services() -> None:
    manifest = _build_manifest()
    contracts = {service.contract for service in manifest.services}
    assert contracts == {DatabaseProvider, UnitOfWork, DatabaseInstaller}


def test_provider_service_is_singleton_and_uow_is_transient() -> None:
    manifest = _build_manifest()
    lifetimes = {service.contract: service.lifetime for service in manifest.services}
    assert lifetimes[DatabaseProvider] is Lifetime.SINGLETON
    assert lifetimes[UnitOfWork] is Lifetime.TRANSIENT
    assert lifetimes[DatabaseInstaller] is Lifetime.SINGLETON


def test_declares_the_six_configuration_keys() -> None:
    manifest = _build_manifest()
    keys = {configuration.key for configuration in manifest.configuration}
    assert keys == {"dialect", "database", "host", "port", "username", "password", "pool_size"}


def test_password_configuration_is_sensitive() -> None:
    manifest = _build_manifest()
    password = next(c for c in manifest.configuration if c.key == "password")
    assert password.sensitive is True


def test_database_configuration_is_required() -> None:
    manifest = _build_manifest()
    database = next(c for c in manifest.configuration if c.key == "database")
    assert database.required is True


def test_declares_a_single_healthcheck_bound_to_health_check() -> None:
    manifest = _build_manifest()
    assert len(manifest.health_checks) == 1
    healthcheck = manifest.health_checks[0]
    assert healthcheck.name == "database.ping"
    assert healthcheck.check is not None


def test_declares_the_connected_and_disconnected_events() -> None:
    manifest = _build_manifest()
    assert set(manifest.events) == {"database.connected", "database.disconnected"}


def test_tags_include_the_configured_dialect() -> None:
    manifest = _build_manifest()
    assert manifest.descriptor.tags == ("sql", "persistence", "sqlite")
