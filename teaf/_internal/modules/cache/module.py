"""``CacheModule`` — módulo de caché distribuida (Sprint 3.0, ADR-012).

Quinto módulo real construido sobre el Module SDK, y calcado a propósito de
``DatabaseModule``: construir no abre conexiones, ``start()`` conecta y
refresca la salud, ``dispose()`` cierra. Un proveedor de infraestructura de
TEAF se comporta siempre igual, así que quien conozca el de base de datos ya
conoce este.

El núcleo del framework nunca importa Redis: este módulo elige una
implementación de ``CacheProvider`` según la configuración y la registra en
el contenedor bajo el **contrato**, nunca bajo la clase concreta. Un
consumidor resuelve ``CacheProvider`` y no puede saber —ni le importa— si
detrás hay un diccionario o un clúster.
"""

from __future__ import annotations

from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.modules.cache.configuration import CacheBackend, CacheConfiguration
from teaf._internal.modules.cache.health import CacheHealth
from teaf._internal.modules.cache.manifest import build_cache_manifest
from teaf._internal.providers.cache.memory import InMemoryCacheProvider
from teaf._internal.providers.cache.redis import RedisCacheProvider
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


def create_cache_provider(configuration: CacheConfiguration) -> CacheProvider:
    """Elige la implementación de ``CacheProvider`` que pide la configuración.

    Es una función y no un método para poder construir un proveedor suelto
    —en una prueba, en un worker— sin levantar el módulo entero.
    """
    if configuration.backend is CacheBackend.REDIS:
        return RedisCacheProvider(configuration.redis)
    return InMemoryCacheProvider()


class CacheModule(ModuleBase):
    """Almacén clave-valor con expiración, en memoria o sobre Redis."""

    def __init__(self, configuration: CacheConfiguration | None = None) -> None:
        super().__init__()
        self.configuration = configuration or CacheConfiguration()
        self.provider = create_cache_provider(self.configuration)
        self.health = CacheHealth(self.provider)

    def get_manifest(self) -> ModuleManifest:
        return build_cache_manifest(self.configuration, provider=self.provider, health=self.health)

    async def start(self, context: ModuleContext) -> None:
        """Abre el pool y refresca la salud — simétrico con ``dispose``."""
        await self.provider.connect()
        await self.health.refresh()

    async def ready(self, context: ModuleContext) -> None:
        context.logger.info(
            "cache_module_ready",
            extra={
                "context": {
                    "backend": self.configuration.backend.value,
                    "health": self.health.last_known.value,
                }
            },
        )

    async def dispose(self, context: ModuleContext) -> None:
        """Cierra el pool. Que sea simétrico con ``start`` es lo que evita fugas."""
        await self.provider.disconnect()
