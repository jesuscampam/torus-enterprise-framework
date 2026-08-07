"""``build_cache_manifest`` — el ``ModuleManifest`` del módulo de caché (Sprint 3.0).

Separado de ``CacheModule`` por el mismo motivo que en el Database Module:
aquí solo se *describe* el módulo con ``ModuleBuilder``; nada se registra
contra el ``Runtime`` desde este archivo — eso lo hace el SDK durante
``ModuleBase.bootstrap()``.

Sobre las categorías: se usa ``STORAGE`` y no una categoría ``CACHE`` propia
porque añadir un miembro a ``ModuleCategory``/``CapabilityCategory``
ampliaría la superficie pública del framework a cambio de un matiz
cosmético. Una caché es almacenamiento, y la descripción de cada capacidad
deja claro de qué tipo.
"""

from __future__ import annotations

from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.modules.cache.configuration import CacheConfiguration
from teaf._internal.modules.cache.health import CacheHealth
from teaf._internal.runtime.capabilities.enums import CapabilityCategory
from teaf._internal.runtime.container import Lifetime
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.manifest import ModuleManifest


def build_cache_manifest(
    configuration: CacheConfiguration,
    *,
    provider: CacheProvider,
    health: CacheHealth,
) -> ModuleManifest:
    """Construye el manifiesto sobre instancias ya creadas en ``CacheModule.__init__``."""
    return (
        ModuleBuilder(id="cache", name="cache", display_name="Cache")
        .with_version("1.0.0")
        .with_description(
            "Caché distribuida de TEAF: almacén clave-valor con expiración, "
            "en memoria o sobre Redis, con ciclo de vida y health check."
        )
        .with_author("TEAF Team")
        .with_license("MIT")
        .with_category(ModuleCategory.STORAGE)
        .with_tags("cache", "redis", configuration.backend.value)
        .with_documentation("docs/modules/cache/CACHE.md")
        .with_runtime_compatibility(">=0.5.0")
        .with_sdk_compatibility(">=1.0.0")
        .add_capability(
            id="cache",
            name="cache",
            category=CapabilityCategory.STORAGE,
            description="Almacén clave-valor con expiración — capacidad general del módulo.",
        )
        .add_capability(
            id="cache.connection",
            name="cache-connection",
            category=CapabilityCategory.STORAGE,
            description="Ciclo de vida del pool de conexiones (connect/disconnect).",
        )
        .add_capability(
            id="cache.health",
            name="cache-health",
            category=CapabilityCategory.OBSERVABILITY,
            description="Verificación de disponibilidad del almacén de caché.",
        )
        .add_configuration(
            key="backend",
            description="memory | redis",
            required=False,
            default=configuration.backend.value,
        )
        .add_configuration(
            key="redis_url",
            description="URL de conexión (redis:// o rediss:// para TLS)",
            required=False,
            sensitive=True,
        )
        .add_configuration(
            key="key_prefix",
            description="Prefijo de todas las claves",
            required=False,
            default=configuration.redis.key_prefix,
        )
        .add_configuration(
            key="max_connections",
            description="Conexiones máximas del pool",
            required=False,
            default=configuration.redis.max_connections,
        )
        .add_service(
            CacheProvider,
            lambda c: provider,
            lifetime=Lifetime.SINGLETON,
            description="Almacén clave-valor con expiración y ciclo de vida.",
            capabilities=("cache.connection",),
        )
        .add_healthcheck(
            name="cache.ping",
            description="Comprueba que el almacén de caché responde.",
            check=health.check,
        )
        .build()
    )
