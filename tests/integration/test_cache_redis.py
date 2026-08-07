"""Prueba de integración: ``RedisCacheProvider`` contra un Redis real (Sprint 3.0).

**Esta prueba se omite si no hay un Redis levantado.** No es una concesión:
la suite de TEAF tiene que poder ejecutarse en cualquier máquina y en CI sin
infraestructura externa, así que el comportamiento del proveedor se verifica
en ``tests/unit/test_cache_module.py`` contra el doble en memoria. Lo que
aquí se comprueba es lo único que un doble no puede demostrar: que los
comandos que emitimos (``SET``/``PSETEX``/``GET``/``DEL``/``PTTL``/``PING``)
se corresponden con lo que Redis hace de verdad.

Para ejecutarla::

    docker run --rm -d -p 6379:6379 --name teaf-redis redis:7-alpine
    pip install "redis>=5.0"
    python -m pytest tests/integration/test_cache_redis.py -q
    docker stop teaf-redis

La URL se toma de ``TEAF_TEST_REDIS_URL`` si está definida; en su defecto,
``redis://localhost:6379/15`` — la base 15 por convención, para no tocar la
0 de un Redis de desarrollo que se esté usando para otra cosa. Las claves
llevan un prefijo único por ejecución y se borran al terminar.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Awaitable, Callable
from typing import TypeVar

import pytest
from teaf._internal.providers.cache.redis import RedisCacheConfiguration, RedisCacheProvider

_URL = os.environ.get("TEAF_TEST_REDIS_URL", "redis://localhost:6379/15")

T = TypeVar("T")


def _redis_is_reachable() -> tuple[bool, str]:
    """Un ``PING`` real. Es la única forma honesta de saber si hay servidor."""
    try:
        import redis.asyncio as redis_asyncio  # noqa: PLC0415
    except ImportError:
        return False, "el extra opcional 'redis' no está instalado (pip install teaf[redis])"

    async def ping() -> bool:
        client = redis_asyncio.from_url(_URL, socket_connect_timeout=1, socket_timeout=1)
        try:
            return bool(await client.ping())
        finally:
            await client.aclose()

    try:
        return bool(asyncio.run(ping())), ""
    except Exception as exc:  # noqa: BLE001 — cualquier fallo aquí significa "no hay servidor"
        return False, f"no hay un Redis accesible en {_URL}: {type(exc).__name__}"


_REACHABLE, _REASON = _redis_is_reachable()

#: Se evalúa **una vez** al importar el módulo, no por prueba: un intento de
#: conexión por test multiplicaría el coste de recolección en toda máquina
#: sin Redis, que es justamente el caso habitual.
requires_redis = pytest.mark.skipif(not _REACHABLE, reason=_REASON or "Redis no disponible")


def _provider() -> RedisCacheProvider:
    """Proveedor con prefijo único por ejecución — dos ejecuciones no se pisan."""
    return RedisCacheProvider(
        RedisCacheConfiguration(url=_URL, key_prefix=f"teaf-test:{uuid.uuid4().hex[:8]}")
    )


def _connected(operation: Callable[[RedisCacheProvider], Awaitable[T]]) -> T:
    """Conecta, opera y desconecta siempre — incluso si la operación falla.

    Un solo ``asyncio.run`` por prueba, como el resto de la suite: los
    objetos de ``redis.asyncio`` se atan al bucle de eventos en el que se
    crean, igual que los ``asyncio.Lock`` del framework.
    """

    async def run() -> T:
        provider = _provider()
        await provider.connect()
        try:
            return await operation(provider)
        finally:
            await provider.disconnect()

    return asyncio.run(run())


@requires_redis
def test_set_and_get_round_trip_through_real_redis() -> None:
    async def scenario(provider: RedisCacheProvider) -> bytes | None:
        await provider.set("saludo", b"hola")
        return await provider.get("saludo")

    assert _connected(scenario) == b"hola"


@requires_redis
def test_get_returns_none_for_missing_key() -> None:
    async def scenario(provider: RedisCacheProvider) -> bytes | None:
        return await provider.get("clave-que-no-existe")

    assert _connected(scenario) is None


@requires_redis
def test_binary_values_survive_intact() -> None:
    """Los stores guardan cuerpos binarios; Redis no debe reinterpretarlos."""
    payload = bytes(range(256))

    async def scenario(provider: RedisCacheProvider) -> bytes | None:
        await provider.set("binario", payload)
        return await provider.get("binario")

    assert _connected(scenario) == payload


@requires_redis
def test_delete_reports_whether_the_key_existed() -> None:
    async def scenario(provider: RedisCacheProvider) -> tuple[bool, bool]:
        await provider.set("efimera", b"1")
        return await provider.delete("efimera"), await provider.delete("efimera")

    assert _connected(scenario) == (True, False)


@requires_redis
def test_ttl_is_applied_and_reported() -> None:
    """``PSETEX`` fija la expiración y ``PTTL`` la devuelve dentro del margen."""

    async def scenario(provider: RedisCacheProvider) -> float | None:
        await provider.set("con-ttl", b"1", ttl_seconds=30)
        return await provider.ttl("con-ttl")

    remaining = _connected(scenario)
    assert remaining is not None
    assert 29 <= remaining <= 30


@requires_redis
def test_ttl_is_none_for_key_without_expiry() -> None:
    """Redis responde ``-1``; el contrato lo une con ``-2`` en ``None``."""

    async def scenario(provider: RedisCacheProvider) -> float | None:
        await provider.set("sin-ttl", b"1")
        return await provider.ttl("sin-ttl")

    assert _connected(scenario) is None


@requires_redis
def test_key_expires_after_its_ttl() -> None:
    async def scenario(provider: RedisCacheProvider) -> bytes | None:
        await provider.set("caduca", b"1", ttl_seconds=0.05)
        await asyncio.sleep(0.2)
        return await provider.get("caduca")

    assert _connected(scenario) is None


@requires_redis
def test_non_positive_ttl_deletes_the_key() -> None:
    """Redis no sabe expresar un TTL <= 0; el proveedor lo traduce a borrar."""

    async def scenario(provider: RedisCacheProvider) -> bytes | None:
        await provider.set("ya-expirada", b"1")
        await provider.set("ya-expirada", b"2", ttl_seconds=0)
        return await provider.get("ya-expirada")

    assert _connected(scenario) is None


@requires_redis
def test_key_prefix_isolates_two_providers_on_the_same_server() -> None:
    """Es la propiedad que permite compartir una instancia entre aplicaciones."""

    async def scenario() -> tuple[bytes | None, bytes | None]:
        uno = RedisCacheProvider(RedisCacheConfiguration(url=_URL, key_prefix="teaf-test:app-a"))
        dos = RedisCacheProvider(RedisCacheConfiguration(url=_URL, key_prefix="teaf-test:app-b"))
        await uno.connect()
        await dos.connect()
        try:
            await uno.set("compartida", b"de-a")
            return await dos.get("compartida"), await uno.get("compartida")
        finally:
            await uno.delete("compartida")
            await uno.disconnect()
            await dos.disconnect()

    assert asyncio.run(scenario()) == (None, b"de-a")


@requires_redis
def test_ping_and_health_check_are_true_while_connected() -> None:
    async def scenario(provider: RedisCacheProvider) -> tuple[bool, bool]:
        return await provider.ping(), await provider.health_check()

    assert _connected(scenario) == (True, True)


@requires_redis
def test_health_check_is_false_after_disconnect() -> None:
    """El criterio de cierre del sprint: ninguna conexión sobrevive al apagado."""

    async def scenario() -> bool:
        provider = _provider()
        await provider.connect()
        await provider.disconnect()
        return await provider.health_check()

    assert asyncio.run(scenario()) is False
