"""``CapabilityBuilder`` — construcción fluida de una ``Capability``.

Ejemplo (ilustrativo — ninguna capacidad real se construye en Sprint 2.4):

    capability = (
        CapabilityBuilder(id="database.query", name="database-query")
        .with_display_name("Consulta de base de datos")
        .with_category(CapabilityCategory.DATABASE)
        .with_module("database")
        .build()
    )
"""

from __future__ import annotations

from collections.abc import Callable

from teaf._internal.runtime.capabilities.enums import (
    CapabilityCategory,
    CapabilityHealth,
    CapabilityStatus,
)
from teaf._internal.runtime.capabilities.metadata import Capability, CapabilityMetadata


class CapabilityBuilder:
    """Builder fluido: cada ``with_*``/``as_*`` devuelve ``self`` para encadenar llamadas."""

    def __init__(self, *, id: str, name: str) -> None:
        self._id = id
        self._name = name
        self._display_name = name
        self._description = ""
        self._version = "0.0.0"
        self._category = CapabilityCategory.CUSTOM
        self._provider: str | None = None
        self._module: str | None = None
        self._status = CapabilityStatus.REGISTERED
        self._experimental = False
        self._deprecated = False
        self._owner: str | None = None
        self._tags: tuple[str, ...] = ()
        self._documentation: str | None = None
        self._permissions_required: tuple[str, ...] = ()
        self._configuration_required: tuple[str, ...] = ()
        self._dependencies: tuple[str, ...] = ()
        self._health_check: Callable[[], CapabilityHealth] | None = None

    def with_display_name(self, display_name: str) -> CapabilityBuilder:
        self._display_name = display_name
        return self

    def with_description(self, description: str) -> CapabilityBuilder:
        self._description = description
        return self

    def with_version(self, version: str) -> CapabilityBuilder:
        self._version = version
        return self

    def with_category(self, category: CapabilityCategory) -> CapabilityBuilder:
        self._category = category
        return self

    def with_provider(self, provider: str) -> CapabilityBuilder:
        self._provider = provider
        return self

    def with_module(self, module: str) -> CapabilityBuilder:
        self._module = module
        return self

    def with_status(self, status: CapabilityStatus) -> CapabilityBuilder:
        self._status = status
        return self

    def with_owner(self, owner: str) -> CapabilityBuilder:
        self._owner = owner
        return self

    def with_tags(self, *tags: str) -> CapabilityBuilder:
        self._tags = tuple(tags)
        return self

    def with_documentation(self, documentation: str) -> CapabilityBuilder:
        self._documentation = documentation
        return self

    def with_permissions_required(self, *permissions: str) -> CapabilityBuilder:
        self._permissions_required = tuple(permissions)
        return self

    def with_configuration_required(self, *keys: str) -> CapabilityBuilder:
        self._configuration_required = tuple(keys)
        return self

    def with_dependencies(self, *dependencies: str) -> CapabilityBuilder:
        self._dependencies = tuple(dependencies)
        return self

    def with_health_check(self, health_check: Callable[[], CapabilityHealth]) -> CapabilityBuilder:
        self._health_check = health_check
        return self

    def as_experimental(self) -> CapabilityBuilder:
        self._experimental = True
        return self

    def as_deprecated(self) -> CapabilityBuilder:
        self._deprecated = True
        return self

    def build(self) -> Capability:
        """Construye la ``Capability`` final a partir de lo acumulado."""
        metadata = CapabilityMetadata(
            id=self._id,
            name=self._name,
            display_name=self._display_name,
            description=self._description,
            version=self._version,
            category=self._category,
            provider=self._provider,
            module=self._module,
            status=self._status,
            experimental=self._experimental,
            deprecated=self._deprecated,
            owner=self._owner,
            tags=self._tags,
            documentation=self._documentation,
            permissions_required=self._permissions_required,
            configuration_required=self._configuration_required,
            dependencies=self._dependencies,
        )
        return Capability(metadata=metadata, health_check=self._health_check)
