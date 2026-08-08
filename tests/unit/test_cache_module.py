"""Pruebas del módulo de caché y sus proveedores (Sprint 3.0, ADR-012).

La suite **no depende de un Redis externo**: el contrato se prueba contra
``InMemoryCacheProvider``, que es una implementación real y no un simulacro,
y el proveedor de Redis se prueba en lo que se puede comprobar sin servidor
—configuración, ciclo de vida, fallos— más un doble para la lógica de los
tres almacenes distribuidos.

Atar toda la suite a un servicio externo la volvería inejecutable en
cualquier máquina que no lo tenga levantado, y una suite que no se puede
ejecutar deja de ejecutarse.
"""

from __future__ import annotations

import asyncio

import pytest
from teaf._internal.api.models import IdempotencyRecord, RateLimitState
from teaf._internal.api.providers.redis import (
    RedisIdempotencyStore,
    RedisQuotaStore,
    RedisRateLimitStore,
)
from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.core.exceptions import ConfigurationException, InfrastructureException
from teaf._internal.modules.cache.configuration import CacheBackend, CacheConfiguration
from teaf._internal.modules.cache.health import CacheHealth
from teaf._internal.modules.cache.module import CacheModule, create_cache_provider
from teaf._internal.providers.cache.memory import InMemoryCacheProvider
from teaf._internal.providers.cache.redis import RedisCacheConfiguration, RedisCacheProvider
from teaf._internal.runtime.capabilities.enums import CapabilityHealth


async def _conectado() -> InMemoryCacheProvider:
    provider = InMemoryCacheProvider()
    await provider.connect()
    return provider


# -- El contrato, sobre la implementación en memoria ---------------------------------------


def test_set_y_get_devuelven_el_mismo_valor() -> None:
    async def _run() -> bytes | None:
        provider = await _conectado()
        await provider.set("clave", b"valor")
        return await provider.get("clave")

    assert asyncio.run(_run()) == b"valor"


def test_get_de_una_clave_inexistente_es_none() -> None:
    async def _run() -> bytes | None:
        return await (await _conectado()).get("no-existe")

    assert asyncio.run(_run()) is None


def test_delete_informa_de_si_habia_algo() -> None:
    async def _run() -> tuple[bool, bool]:
        provider = await _conectado()
        await provider.set("clave", b"v")
        return await provider.delete("clave"), await provider.delete("clave")

    assert asyncio.run(_run()) == (True, False)


def test_una_clave_con_ttl_vencido_no_se_devuelve() -> None:
    async def _run() -> bytes | None:
        provider = await _conectado()
        await provider.set("efimera", b"v", ttl_seconds=-1)
        return await provider.get("efimera")

    assert asyncio.run(_run()) is None


def test_ttl_devuelve_lo_que_queda_y_none_sin_expiracion() -> None:
    async def _run() -> tuple[float | None, float | None, float | None]:
        provider = await _conectado()
        await provider.set("con-ttl", b"v", ttl_seconds=60)
        await provider.set("sin-ttl", b"v")
        return (
            await provider.ttl("con-ttl"),
            await provider.ttl("sin-ttl"),
            await provider.ttl("no-existe"),
        )

    restante, sin_ttl, ausente = asyncio.run(_run())
    assert restante is not None and 0 < restante <= 60
    assert sin_ttl is None
    assert ausente is None


def test_la_memoria_queda_acotada_por_la_purga_amortizada() -> None:
    """Mismo criterio que Sprint 2.9.1: caducar solo al leer deja crecer sin techo."""

    async def _run() -> int:
        provider = await _conectado()
        for n in range(1_536):
            await provider.set(f"clave-{n}", b"v", ttl_seconds=-1)
        return provider.size

    assert asyncio.run(_run()) < 100


def test_desconectar_vacia_el_estado() -> None:
    """Heredar datos de un arranque anterior convierte fallos reales en intermitentes."""

    async def _run() -> tuple[int, bool]:
        provider = await _conectado()
        await provider.set("clave", b"v")
        await provider.disconnect()
        return provider.size, await provider.ping()

    assert asyncio.run(_run()) == (0, False)


def test_ping_es_falso_antes_de_conectar() -> None:
    assert asyncio.run(InMemoryCacheProvider().ping()) is False


# -- Configuración del proveedor Redis -----------------------------------------------------


@pytest.mark.parametrize("url", ["redis://host:6379/0", "rediss://host:6379/0", "unix:///tmp/r"])
def test_urls_validas_se_aceptan(url: str) -> None:
    assert RedisCacheProvider(RedisCacheConfiguration(url=url)) is not None


@pytest.mark.parametrize("url", ["", "   ", "http://host", "localhost:6379"])
def test_urls_invalidas_se_rechazan_al_construir(url: str) -> None:
    with pytest.raises(ConfigurationException):
        RedisCacheProvider(RedisCacheConfiguration(url=url))


def test_un_pool_de_tamano_invalido_se_rechaza() -> None:
    with pytest.raises(ConfigurationException):
        RedisCacheProvider(RedisCacheConfiguration(max_connections=0))


def test_construir_no_abre_ninguna_conexion() -> None:
    """Construir es barato y sin efectos, igual que en DatabaseModule."""
    provider = RedisCacheProvider()
    assert provider._client is None
    assert asyncio.run(provider.health_check()) is False


def test_operar_sin_conectar_falla_con_un_mensaje_util() -> None:
    with pytest.raises(InfrastructureException, match="connect"):
        asyncio.run(RedisCacheProvider().get("clave"))


def test_el_prefijo_aisla_las_claves_entre_aplicaciones() -> None:
    provider = RedisCacheProvider(RedisCacheConfiguration(key_prefix="app-a"))
    assert provider.key("sesion") == "app-a:sesion"


def test_sin_prefijo_la_clave_no_se_modifica() -> None:
    provider = RedisCacheProvider(RedisCacheConfiguration(key_prefix=""))
    assert provider.key("sesion") == "sesion"


def test_desconectar_sin_haber_conectado_no_falla() -> None:
    """Idempotencia del apagado: el ciclo de vida no debe romperse a medias."""
    asyncio.run(RedisCacheProvider().disconnect())


@pytest.mark.parametrize(
    ("url", "espera_tls"),
    [
        ("redis://host:6379/0", False),
        ("unix:///tmp/redis.sock", False),
        ("rediss://host:6379/0", True),
    ],
)
def test_solo_una_url_rediss_se_considera_tls(url: str, espera_tls: bool) -> None:
    """Regresión: ``ssl_cert_reqs`` solo lo acepta ``SSLConnection``.

    Pasarlo sobre una URL ``redis://`` hacía fallar con ``TypeError`` la
    primera operación —no ``connect()``, porque ``from_url`` es perezoso—,
    de modo que el backend por defecto quedaba inutilizable. Lo detectó
    ``tests/integration/test_cache_redis.py`` contra un Redis real; esto lo
    fija sin necesitar servidor.
    """
    assert RedisCacheProvider(RedisCacheConfiguration(url=url)).uses_tls is espera_tls


# -- Configuración del módulo --------------------------------------------------------------


def test_el_backend_por_defecto_es_memoria() -> None:
    """TEAF debe arrancar sin infraestructura desplegada."""
    assert CacheConfiguration().backend is CacheBackend.MEMORY
    assert isinstance(create_cache_provider(CacheConfiguration()), InMemoryCacheProvider)


def test_el_backend_redis_construye_el_proveedor_de_redis() -> None:
    config = CacheConfiguration(backend=CacheBackend.REDIS)
    assert isinstance(create_cache_provider(config), RedisCacheProvider)


def test_from_mapping_reconoce_el_prefijo_cache() -> None:
    config = CacheConfiguration.from_mapping(
        {
            "cache_enabled": "true",
            "cache_backend": "redis",
            "cache_redis_url": "rediss://prod:6379/1",
            "cache_max_connections": "25",
            "cache_tls_verify": "false",
        }
    )
    assert config.enabled is True
    assert config.backend is CacheBackend.REDIS
    assert config.redis.url == "rediss://prod:6379/1"
    assert config.redis.max_connections == 25
    assert config.redis.tls_verify is False


def test_un_backend_desconocido_se_rechaza_con_las_opciones() -> None:
    with pytest.raises(ConfigurationException, match="memory"):
        CacheConfiguration.from_mapping({"cache_backend": "memcached"})


# -- Ciclo de vida del módulo --------------------------------------------------------------


def test_el_modulo_conecta_al_arrancar_y_cierra_al_apagar() -> None:
    """Lo que evita fugas es que ``start`` y ``dispose`` sean simétricos."""

    async def _run() -> tuple[bool, bool]:
        module = CacheModule()
        contexto = _contexto_falso()
        await module.start(contexto)
        conectado = await module.provider.ping()
        await module.dispose(contexto)
        return conectado, await module.provider.ping()

    assert asyncio.run(_run()) == (True, False)


def test_el_manifiesto_declara_capacidades_servicio_y_health() -> None:
    manifest = CacheModule().get_manifest()
    assert manifest.descriptor.id == "cache"
    assert {c.id for c in manifest.capabilities} >= {"cache", "cache.connection", "cache.health"}
    assert any(s.contract is CacheProvider for s in manifest.services)
    assert [h.name for h in manifest.health_checks] == ["cache.ping"]


def test_la_salud_pasa_de_desconocida_a_sana_tras_arrancar() -> None:
    async def _run() -> tuple[CapabilityHealth, CapabilityHealth]:
        module = CacheModule()
        antes = module.health.check()
        await module.start(_contexto_falso())
        return antes, module.health.check()

    antes, despues = asyncio.run(_run())
    assert antes is CapabilityHealth.UNKNOWN
    assert despues is CapabilityHealth.HEALTHY


def test_la_salud_es_no_sana_si_el_proveedor_no_responde() -> None:
    """Un Redis caído debe reportarse como no sano, no lanzar."""

    class _Caido(InMemoryCacheProvider):
        async def health_check(self) -> bool:
            return False

    health = CacheHealth(_Caido())
    assert asyncio.run(health.refresh()) is CapabilityHealth.UNHEALTHY


def _contexto_falso() -> object:
    """``ModuleContext`` mínimo: ``start``/``dispose`` solo usan el logger en ``ready``."""

    class _Contexto:
        import logging as _logging

        logger = _logging.getLogger("tests.cache")

    return _Contexto()


# -- Los tres almacenes distribuidos, sobre el doble en memoria -----------------------------


def test_el_almacen_de_rate_limit_conserva_el_estado_completo() -> None:
    """El estado es opaco para el almacén: debe volver idéntico."""

    async def _run() -> RateLimitState | None:
        store = RedisRateLimitStore(await _conectado())
        estado = RateLimitState(
            tokens=3.5, updated_at=100.0, count=7, window_start=90.0, timestamps=(1.0, 2.0)
        )
        await store.put("ip:1.2.3.4", estado, ttl_seconds=60)
        return await store.get("ip:1.2.3.4")

    recuperado = asyncio.run(_run())
    assert recuperado == RateLimitState(
        tokens=3.5, updated_at=100.0, count=7, window_start=90.0, timestamps=(1.0, 2.0)
    )


def test_el_almacen_de_rate_limit_devuelve_none_si_no_hay_estado() -> None:
    async def _run() -> RateLimitState | None:
        return await RedisRateLimitStore(await _conectado()).get("sin-estado")

    assert asyncio.run(_run()) is None


def test_reset_borra_el_estado_del_limitador() -> None:
    async def _run() -> RateLimitState | None:
        store = RedisRateLimitStore(await _conectado())
        await store.put("k", RateLimitState(), ttl_seconds=60)
        await store.reset("k")
        return await store.get("k")

    assert asyncio.run(_run()) is None


def test_la_cuota_acumula_y_libera_sin_bajar_de_cero() -> None:
    async def _run() -> tuple[float, float, float]:
        store = RedisQuotaStore(await _conectado())
        primero = await store.consume("tenant:a", 3.0, ttl_seconds=60)
        segundo = await store.consume("tenant:a", 2.0, ttl_seconds=60)
        liberado = await store.release("tenant:a", 100.0)
        return primero, segundo, liberado

    assert asyncio.run(_run()) == (3.0, 5.0, 0.0)


def test_peek_de_una_cuota_sin_consumo_es_cero() -> None:
    async def _run() -> float:
        return await RedisQuotaStore(await _conectado()).peek("nueva")

    assert asyncio.run(_run()) == 0.0


def test_los_tres_almacenes_no_se_pisan_las_claves() -> None:
    """Cada uno vive en su propio espacio de nombres dentro del mismo Redis."""

    async def _run() -> tuple[float, RateLimitState | None]:
        provider = await _conectado()
        cuota = RedisQuotaStore(provider)
        limite = RedisRateLimitStore(provider)
        await cuota.consume("misma-clave", 9.0, ttl_seconds=60)
        return await cuota.peek("misma-clave"), await limite.get("misma-clave")

    consumo, estado = asyncio.run(_run())
    assert consumo == 9.0
    assert estado is None


def test_la_idempotencia_reproduce_la_respuesta_con_su_cuerpo_binario() -> None:
    """El cuerpo puede venir comprimido: debe volver byte a byte."""

    async def _run() -> IdempotencyRecord | None:
        store = RedisIdempotencyStore(await _conectado())
        registro = IdempotencyRecord(
            key="pago-1",
            fingerprint="abc",
            status_code=201,
            body=b"\x1f\x8b\x08\x00binario",
            headers={"content-type": "application/json"},
            created_at=100.0,
            expires_at=160.0,
        )
        await store.put(registro)
        return await store.get("pago-1")

    recuperado = asyncio.run(_run())
    assert recuperado is not None
    assert recuperado.body == b"\x1f\x8b\x08\x00binario"
    assert recuperado.status_code == 201
    assert recuperado.headers == {"content-type": "application/json"}


def test_borrar_un_registro_de_idempotencia() -> None:
    async def _run() -> IdempotencyRecord | None:
        store = RedisIdempotencyStore(await _conectado())
        await store.put(
            IdempotencyRecord(
                key="k",
                fingerprint="f",
                status_code=200,
                body=b"",
                headers={},
                created_at=0.0,
                expires_at=60.0,
            )
        )
        await store.delete("k")
        return await store.get("k")

    assert asyncio.run(_run()) is None
