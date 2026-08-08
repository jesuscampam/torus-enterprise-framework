"""``ModuleBuilder`` — construcción fluida de un ``ModuleManifest``.

Ejemplo (ilustrativo — ningún módulo real se construye en este Sprint):

    manifest = (
        ModuleBuilder(id="database", name="database", display_name="Database")
        .with_category(ModuleCategory.DATABASE)
        .add_service(DatabaseProvider, lambda c: PostgresProvider())
        .add_capability(id="database.query", name="database-query")
        .add_event("database.connected")
        .add_healthcheck(name="database.ping")
        .add_dependency(module_id="security")
        .build()
    )
"""

from __future__ import annotations

from collections.abc import Callable

from teaf._internal.runtime.capabilities.enums import CapabilityCategory, CapabilityHealth
from teaf._internal.runtime.container import Factory, Lifetime
from teaf._internal.sdk.capability import ModuleCapability
from teaf._internal.sdk.configuration import ModuleConfiguration
from teaf._internal.sdk.dependency import ModuleDependency
from teaf._internal.sdk.descriptor import ModuleDescriptor
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.health import ModuleHealth
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.service import ModuleService


class ModuleBuilder:
    """Builder fluido: cada ``with_*``/``add_*`` devuelve ``self`` para encadenar llamadas."""

    def __init__(self, *, id: str, name: str, display_name: str | None = None) -> None:
        self._id = id
        self._name = name
        self._display_name = display_name or name
        self._version = "0.0.0"
        self._description = ""
        self._author: str | None = None
        self._category = ModuleCategory.GENERIC
        self._tags: tuple[str, ...] = ()
        self._documentation: str | None = None
        self._experimental = False
        self._deprecated = False
        self._license: str | None = None
        self._capabilities: list[ModuleCapability] = []
        self._dependencies: list[ModuleDependency] = []
        self._configuration: list[ModuleConfiguration] = []
        self._services: list[ModuleService] = []
        self._health_checks: list[ModuleHealth] = []
        self._events: list[str] = []
        self._runtime_compatibility = "*"
        self._sdk_compatibility = "*"

    def with_display_name(self, display_name: str) -> ModuleBuilder:
        self._display_name = display_name
        return self

    def with_version(self, version: str) -> ModuleBuilder:
        self._version = version
        return self

    def with_description(self, description: str) -> ModuleBuilder:
        self._description = description
        return self

    def with_author(self, author: str) -> ModuleBuilder:
        self._author = author
        return self

    def with_license(self, license_: str) -> ModuleBuilder:
        self._license = license_
        return self

    def with_category(self, category: ModuleCategory) -> ModuleBuilder:
        self._category = category
        return self

    def with_tags(self, *tags: str) -> ModuleBuilder:
        self._tags = tuple(tags)
        return self

    def with_documentation(self, documentation: str) -> ModuleBuilder:
        self._documentation = documentation
        return self

    def with_runtime_compatibility(self, constraint: str) -> ModuleBuilder:
        self._runtime_compatibility = constraint
        return self

    def with_sdk_compatibility(self, constraint: str) -> ModuleBuilder:
        self._sdk_compatibility = constraint
        return self

    def as_experimental(self) -> ModuleBuilder:
        self._experimental = True
        return self

    def as_deprecated(self) -> ModuleBuilder:
        self._deprecated = True
        return self

    def add_capability(
        self,
        *,
        id: str,
        name: str,
        category: CapabilityCategory = CapabilityCategory.CUSTOM,
        description: str = "",
        tags: tuple[str, ...] = (),
        experimental: bool = False,
    ) -> ModuleBuilder:
        self._capabilities.append(
            ModuleCapability(
                id=id,
                name=name,
                category=category,
                description=description,
                tags=tags,
                experimental=experimental,
            )
        )
        return self

    def add_dependency(
        self, *, module_id: str, version_constraint: str | None = None, optional: bool = False
    ) -> ModuleBuilder:
        self._dependencies.append(
            ModuleDependency(
                module_id=module_id, version_constraint=version_constraint, optional=optional
            )
        )
        return self

    def add_configuration(
        self,
        *,
        key: str,
        description: str = "",
        required: bool = False,
        default: object | None = None,
        sensitive: bool = False,
    ) -> ModuleBuilder:
        self._configuration.append(
            ModuleConfiguration(
                key=key,
                description=description,
                required=required,
                default=default,
                sensitive=sensitive,
            )
        )
        return self

    def add_service(
        self,
        contract: type,
        factory: Factory[object],
        *,
        lifetime: Lifetime = Lifetime.SINGLETON,
        description: str = "",
        tags: tuple[str, ...] = (),
        capabilities: tuple[str, ...] = (),
    ) -> ModuleBuilder:
        self._services.append(
            ModuleService(
                contract=contract,
                factory=factory,
                lifetime=lifetime,
                description=description,
                tags=tags,
                capabilities=capabilities,
            )
        )
        return self

    def add_healthcheck(
        self,
        *,
        name: str,
        description: str = "",
        check: Callable[[], CapabilityHealth] | None = None,
    ) -> ModuleBuilder:
        self._health_checks.append(ModuleHealth(name=name, description=description, check=check))
        return self

    def add_event(self, event_name: str) -> ModuleBuilder:
        self._events.append(event_name)
        return self

    def build(self) -> ModuleManifest:
        """Construye el ``ModuleManifest`` final a partir de lo acumulado."""
        descriptor = ModuleDescriptor(
            id=self._id,
            name=self._name,
            display_name=self._display_name,
            version=self._version,
            description=self._description,
            author=self._author,
            category=self._category,
            tags=self._tags,
            documentation=self._documentation,
            experimental=self._experimental,
            deprecated=self._deprecated,
        )
        return ModuleManifest(
            descriptor=descriptor,
            license=self._license,
            capabilities=tuple(self._capabilities),
            dependencies=tuple(self._dependencies),
            configuration=tuple(self._configuration),
            services=tuple(self._services),
            health_checks=tuple(self._health_checks),
            events=tuple(self._events),
            runtime_compatibility=self._runtime_compatibility,
            sdk_compatibility=self._sdk_compatibility,
        )
