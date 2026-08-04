"""``ServiceContainer`` — resolución de dependencias por contrato.

Contenedor de inyección de dependencias del Runtime. Es deliberadamente
genérico: resuelve por cualquier ``type`` (típicamente una interfaz de
``backend/contracts/``, pero el contenedor mismo no importa ese paquete —
no conoce ni le importa qué es un "contrato", solo indexa por tipo).

Soporta tres ciclos de vida (``Lifetime``), resolución perezosa (ningún
factory se ejecuta hasta el primer ``resolve()``) y detección de
dependencias circulares entre factories que se resuelven unas a otras.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, Generic, TypeVar, cast

from teaf._internal.runtime.exceptions import (
    CircularDependencyException,
    ServiceNotRegisteredException,
)

T = TypeVar("T")

#: Una factory recibe el propio contenedor — puede resolver otras
#: dependencias registradas para construir la suya.
Factory = Callable[["ServiceContainer"], T]

_UNSET = object()


class Lifetime(str, Enum):
    """Ciclo de vida de un servicio registrado en el contenedor."""

    #: Una única instancia por contenedor, creada en el primer ``resolve()``.
    SINGLETON = "singleton"
    #: Una instancia por ``ServiceScope``, compartida dentro de ese ámbito.
    SCOPED = "scoped"
    #: Una instancia nueva en cada ``resolve()``.
    TRANSIENT = "transient"


class ServiceHealth(str, Enum):
    """Salud declarada de un servicio registrado, sin verificación en vivo.

    Vocabulario propio y decoupled de ``CapabilityHealth``
    (``backend/runtime/capabilities/enums.py``) — servicios y capacidades son
    conceptos distintos, aunque compartan la forma "unknown/healthy/degraded".
    """

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class ServiceMetadata:
    """Metadata descriptiva de un servicio, expuesta por ``GET /runtime/services``."""

    service_id: str
    name: str
    lifetime: Lifetime
    module: str | None = None
    factory: str | None = None
    dependencies: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    health: ServiceHealth = ServiceHealth.UNKNOWN
    description: str = ""
    version: str = "0.0.0"
    tags: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta metadata."""
        return {
            "serviceId": self.service_id,
            "name": self.name,
            "lifetime": self.lifetime.value,
            "module": self.module,
            "factory": self.factory,
            "dependencies": list(self.dependencies),
            "capabilities": list(self.capabilities),
            "health": self.health.value,
            "description": self.description,
            "version": self.version,
            "tags": list(self.tags),
        }


class _Registration:
    __slots__ = ("contract", "factory", "lifetime", "metadata")

    def __init__(
        self,
        contract: type,
        factory: Factory[Any],
        lifetime: Lifetime,
        metadata: ServiceMetadata | None = None,
    ) -> None:
        self.contract = contract
        self.factory = factory
        self.lifetime = lifetime
        self.metadata = metadata


class Lazy(Generic[T]):
    """Resolución diferida: ``factory`` no se invoca hasta acceder a ``.value``."""

    def __init__(self, factory: Callable[[], T]) -> None:
        self._factory = factory
        self._value: T | object = _UNSET

    @property
    def value(self) -> T:
        """Resuelve (una sola vez) y devuelve el valor envuelto."""
        if self._value is _UNSET:
            self._value = self._factory()
        return cast(T, self._value)

    @property
    def is_resolved(self) -> bool:
        """``True`` si ``.value`` ya se accedió al menos una vez."""
        return self._value is not _UNSET


class ServiceScope:
    """Ámbito de resolución para servicios ``Lifetime.SCOPED``.

    Se crea con ``ServiceContainer.create_scope()`` y se usa como gestor de
    contexto: los contratos ``SCOPED`` resueltos dentro del mismo ``with``
    comparten instancia; ámbitos distintos nunca comparten nada entre sí.
    """

    def __init__(self, container: ServiceContainer) -> None:
        self._container = container
        self._instances: dict[type, Any] = {}

    def resolve(self, contract: type[T]) -> T:
        """Resuelve ``contract`` dentro de este ámbito."""
        return self._container._resolve(contract, scope=self)

    def __enter__(self) -> ServiceScope:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._instances.clear()


class ServiceContainer:
    """Registra y resuelve servicios por contrato."""

    def __init__(self) -> None:
        self._registrations: dict[type, _Registration] = {}
        self._singletons: dict[type, Any] = {}
        self._resolving: list[type] = []

    def register_singleton(
        self, contract: type[T], factory: Factory[T], *, metadata: ServiceMetadata | None = None
    ) -> None:
        """Registra ``factory`` como proveedor único de ``contract`` para todo el contenedor."""
        self._registrations[contract] = _Registration(
            contract, factory, Lifetime.SINGLETON, metadata
        )

    def register_scoped(
        self, contract: type[T], factory: Factory[T], *, metadata: ServiceMetadata | None = None
    ) -> None:
        """Registra ``factory`` de ``contract``: una instancia por ``ServiceScope``."""
        self._registrations[contract] = _Registration(contract, factory, Lifetime.SCOPED, metadata)

    def register_transient(
        self, contract: type[T], factory: Factory[T], *, metadata: ServiceMetadata | None = None
    ) -> None:
        """Registra ``factory`` de ``contract``: nueva instancia en cada resolución."""
        self._registrations[contract] = _Registration(
            contract, factory, Lifetime.TRANSIENT, metadata
        )

    def register_instance(
        self, contract: type[T], instance: T, *, metadata: ServiceMetadata | None = None
    ) -> None:
        """Registra ``instance`` ya construida como singleton (sin factory diferida)."""
        self._registrations[contract] = _Registration(
            contract, lambda _c: instance, Lifetime.SINGLETON, metadata
        )
        self._singletons[contract] = instance

    def unregister(self, contract: type) -> None:
        """Elimina el proveedor registrado de ``contract`` (y su singleton, si existía).

        Raises:
            ServiceNotRegisteredException: si ``contract`` no tiene proveedor
                registrado.
        """
        if contract not in self._registrations:
            raise ServiceNotRegisteredException(
                f"No hay ningún proveedor registrado para '{contract.__name__}'."
            )
        del self._registrations[contract]
        self._singletons.pop(contract, None)

    def is_registered(self, contract: type) -> bool:
        """``True`` si ``contract`` tiene algún proveedor registrado."""
        return contract in self._registrations

    def registered_contracts(self) -> tuple[type, ...]:
        """Todos los contratos con proveedor registrado (consultado por ``/info``)."""
        return tuple(self._registrations.keys())

    def describe_services(self) -> tuple[ServiceMetadata, ...]:
        """Metadata de todos los servicios registrados, consultada por la Runtime API.

        Un contrato registrado sin ``metadata`` explícita obtiene una
        ``ServiceMetadata`` mínima sintetizada a partir de su ``contract`` y
        ``lifetime`` — ``describe_services`` siempre describe el 100% de los
        contratos registrados, con o sin metadata aportada.
        """
        described: list[ServiceMetadata] = []
        for contract, registration in self._registrations.items():
            if registration.metadata is not None:
                described.append(registration.metadata)
            else:
                described.append(
                    ServiceMetadata(
                        service_id=contract.__name__,
                        name=contract.__name__,
                        lifetime=registration.lifetime,
                    )
                )
        return tuple(described)

    def resolve(self, contract: type[T]) -> T:
        """Resuelve ``contract`` fuera de cualquier ``ServiceScope``.

        Raises:
            ServiceNotRegisteredException: si nadie registró ``contract``, o
                si está registrado como ``SCOPED`` y se resuelve sin ámbito.
            CircularDependencyException: si dos o más factories se resuelven
                entre sí formando un ciclo.
        """
        return self._resolve(contract, scope=None)

    def resolve_lazy(self, contract: type[T]) -> Lazy[T]:
        """Como ``resolve``, pero devuelve un ``Lazy[T]`` que difiere la resolución real."""
        return Lazy(lambda: self.resolve(contract))

    def create_scope(self) -> ServiceScope:
        """Crea un nuevo ``ServiceScope`` para resolver servicios ``SCOPED``."""
        return ServiceScope(self)

    def _resolve(self, contract: type[T], *, scope: ServiceScope | None) -> T:
        registration = self._registrations.get(contract)
        if registration is None:
            raise ServiceNotRegisteredException(
                f"No hay ningún proveedor registrado para '{contract.__name__}'."
            )

        if registration.lifetime is Lifetime.SINGLETON:
            if contract in self._singletons:
                return cast(T, self._singletons[contract])
            instance = self._instantiate(registration)
            self._singletons[contract] = instance
            return cast(T, instance)

        if registration.lifetime is Lifetime.SCOPED:
            if scope is None:
                raise ServiceNotRegisteredException(
                    f"'{contract.__name__}' está registrado como Scoped: resuélvelo "
                    "dentro de un ServiceScope (container.create_scope())."
                )
            if contract in scope._instances:
                return cast(T, scope._instances[contract])
            instance = self._instantiate(registration)
            scope._instances[contract] = instance
            return cast(T, instance)

        # TRANSIENT: nunca se cachea.
        return cast(T, self._instantiate(registration))

    def _instantiate(self, registration: _Registration) -> Any:
        contract = registration.contract
        if contract in self._resolving:
            chain = " -> ".join(c.__name__ for c in [*self._resolving, contract])
            raise CircularDependencyException(f"Dependencia circular al resolver: {chain}")
        self._resolving.append(contract)
        try:
            return registration.factory(self)
        finally:
            self._resolving.pop()
