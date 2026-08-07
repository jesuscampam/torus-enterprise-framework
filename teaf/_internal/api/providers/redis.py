"""Proveedores distribuidos sobre Redis para la protección de APIs (Sprint 3.0, ADR-012).

Hasta Sprint 2.9.2 estas tres clases eran **contratos preparados**: cumplían
las interfaces de ``contracts/api.py``, documentaban qué comando de Redis
implementaría cada operación y lanzaban ``NotImplementedError``, porque
``redis-py`` no formaba parte del stack. Sprint 3.0 aprueba la dependencia
(ADR-012) y sustituye cada cuerpo por la llamada que su docstring ya
describía.

ADR-009 se fijó como criterio de éxito que implementarlas no cambiara
**ninguna** firma. Se cumple para las operaciones —``get``/``put``/
``reset``/``consume``/``peek``/``release``/``store``/``fetch``/``delete``
son idénticas—, para el registro en DI y para la configuración del módulo,
pero **no para el constructor**: los tres pasan de ``(url, prefix)`` a
recibir un ``CacheProvider``. La ruptura es deliberada y está justificada en
ADR-012 §5; el motivo es que ``(url, prefix)`` daba a cada almacén su propia
conexión sin nadie que la cerrara, y una conexión que sobrevive al apagado
es precisamente lo que Sprint 3.0 se marcó como criterio de bloqueo. No
puede romper a ningún consumidor real porque hasta 2.9.2 el constructor
lanzaba ``NotImplementedError`` incondicionalmente: no existe una llamada
que antes funcionara y ahora falle.

Por qué existen: los almacenes en memoria son por proceso, así que con
varias réplicas cada una lleva su propia cuenta y un límite de 100
peticiones por minuto con 4 réplicas son 400. Estos tres comparten el estado
y hacen que el límite signifique lo que dice.

Los tres se apoyan en ``CacheProvider`` (``contracts/cache.py``) y no en un
cliente de Redis propio: así el ciclo de vida de la conexión —abrirla,
cerrarla, vigilar su salud— lo lleva el módulo de caché en un solo sitio, y
estos objetos se limitan a su lógica. Ninguno abre conexiones.
"""

from __future__ import annotations

import json
from base64 import b64decode, b64encode
from typing import Any

from teaf._internal.api.models import IdempotencyRecord, RateLimitState
from teaf._internal.contracts.api import IdempotencyStore, QuotaStore, RateLimitStore
from teaf._internal.contracts.cache import CacheProvider


class _RedisBackedStore:
    """Base común: el proveedor de caché y el espacio de nombres de las claves."""

    #: Prefijo que separa los tres almacenes dentro de la misma instancia de
    #: Redis. Sin él, una clave de cuota y una de rate limiting con el mismo
    #: identificador se pisarían.
    namespace = ""

    def __init__(self, provider: CacheProvider) -> None:
        self.provider = provider

    def key(self, key: str) -> str:
        return f"{self.namespace}:{key}"


class RedisRateLimitStore(_RedisBackedStore, RateLimitStore):
    """``RateLimitStore`` distribuido sobre Redis.

    El estado viaja serializado como JSON en una sola clave con TTL. El
    contrato trata el estado como **opaco** (ver ``contracts/api.py``), así
    que los cuatro algoritmos —ventana fija, ventana deslizante, token
    bucket, leaky bucket— comparten esta misma implementación sin que
    ninguno necesite un tipo de dato distinto de Redis.
    """

    namespace = "rl"

    async def get(self, key: str) -> RateLimitState | None:
        raw = await self.provider.get(self.key(key))
        if raw is None:
            return None
        data: dict[str, Any] = json.loads(raw)
        return RateLimitState(
            tokens=float(data["tokens"]),
            updated_at=float(data["updated_at"]),
            count=int(data["count"]),
            window_start=float(data["window_start"]),
            timestamps=tuple(float(t) for t in data["timestamps"]),
        )

    async def put(self, key: str, state: RateLimitState, *, ttl_seconds: float) -> None:
        payload = json.dumps(
            {
                "tokens": state.tokens,
                "updated_at": state.updated_at,
                "count": state.count,
                "window_start": state.window_start,
                "timestamps": list(state.timestamps),
            }
        ).encode("utf-8")
        await self.provider.set(self.key(key), payload, ttl_seconds=ttl_seconds)

    async def reset(self, key: str) -> None:
        await self.provider.delete(self.key(key))


class RedisQuotaStore(_RedisBackedStore, QuotaStore):
    """``QuotaStore`` distribuido sobre Redis.

    **Limitación conocida, y es importante no darla por resuelta**: esta
    implementación consume con «leer, sumar, escribir» sobre
    ``CacheProvider``, que no es atómico entre instancias. Bajo consumo
    simultáneo de varias réplicas sobre la *misma* clave de cuota, dos
    incrementos pueden solaparse y contar de menos.

    La solución correcta es ``INCRBYFLOAT``, que Redis ejecuta de forma
    atómica, pero exige ampliar ``CacheProvider`` con una operación de
    incremento — es decir, ampliar el contrato para un caso que aún no ha
    aparecido en producción. Se documenta y se deja en el backlog en vez de
    ampliarlo especulativamente ([CLAUDE.md](../../../../CLAUDE.md) §3): las
    cuotas son contadores de consumo contratado, con ventanas de minutos a
    meses, donde una desviación puntual bajo concurrencia extrema no tiene
    el mismo coste que en un limitador de disponibilidad.
    """

    namespace = "q"

    async def consume(self, key: str, amount: float, *, ttl_seconds: float) -> float:
        current = await self.peek(key)
        updated = current + amount
        await self.provider.set(
            self.key(key), str(updated).encode("utf-8"), ttl_seconds=ttl_seconds
        )
        return updated

    async def peek(self, key: str) -> float:
        raw = await self.provider.get(self.key(key))
        return float(raw) if raw is not None else 0.0

    async def release(self, key: str, amount: float) -> float:
        """Devuelve consumo a la cuota, acotado a 0.

        Conserva el TTL restante en vez de reiniciarlo: liberar una cuota de
        concurrencia no debe prolongar la ventana de consumo.
        """
        remaining_ttl = await self.provider.ttl(self.key(key))
        updated = max(await self.peek(key) - amount, 0.0)
        await self.provider.set(
            self.key(key), str(updated).encode("utf-8"), ttl_seconds=remaining_ttl
        )
        return updated

    async def reset(self, key: str) -> None:
        await self.provider.delete(self.key(key))


class RedisIdempotencyStore(_RedisBackedStore, IdempotencyStore):
    """``IdempotencyStore`` distribuido sobre Redis.

    El cuerpo de la respuesta se guarda en base64 dentro del JSON: es
    ``bytes`` arbitrarios —puede venir comprimido— y JSON no admite bytes
    crudos. El coste en tamaño (~33%) se acepta a cambio de un formato
    legible y depurable.
    """

    namespace = "idem"

    async def get(self, key: str) -> IdempotencyRecord | None:
        raw = await self.provider.get(self.key(key))
        if raw is None:
            return None
        data: dict[str, Any] = json.loads(raw)
        return IdempotencyRecord(
            key=data["key"],
            fingerprint=data["fingerprint"],
            status_code=int(data["status_code"]),
            body=b64decode(data["body"]),
            headers=dict(data["headers"]),
            created_at=float(data["created_at"]),
            expires_at=float(data["expires_at"]),
        )

    async def put(self, record: IdempotencyRecord) -> None:
        payload = json.dumps(
            {
                "key": record.key,
                "fingerprint": record.fingerprint,
                "status_code": record.status_code,
                "body": b64encode(record.body).decode("ascii"),
                "headers": dict(record.headers),
                "created_at": record.created_at,
                "expires_at": record.expires_at,
            }
        ).encode("utf-8")
        # El TTL sale del propio registro para que la entrada caduque a la vez
        # en Redis y según su ``expires_at`` — si divergieran, una respuesta
        # podría reproducirse después de haber expirado.
        ttl = max(record.expires_at - record.created_at, 0.0)
        await self.provider.set(self.key(record.key), payload, ttl_seconds=ttl)

    async def delete(self, key: str) -> None:
        await self.provider.delete(self.key(key))
