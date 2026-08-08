"""Contratos de la plataforma de protección de APIs (Sprint 2.9, ADR-009).

Mismo criterio que ``contracts/security.py`` y ``contracts/telemetry.py``:
aquí viven **solo** las interfaces alrededor de las que se diseña la
plataforma — nunca una implementación concreta, y nunca un tipo de una
librería de terceros filtrado en una firma.

Los cuatro contratos de almacenamiento (``RateLimitStore``, ``QuotaStore``,
``IdempotencyStore``, ``AuditSink``) son ``async`` aunque las
implementaciones en memoria de Sprint 2.9 no hagan I/O: es precisamente lo
que permite sustituirlas por Redis, PostgreSQL o un gateway externo sin
cambiar ni una línea de ``RateLimiter``/``QuotaManager``/
``IdempotencyManager``/``ApiAudit`` (criterio de éxito del Sprint, ver
``api/providers/redis.py``).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from teaf._internal.api.models import (
    ApiAuditRecord,
    CompressionAlgorithm,
    IdempotencyRecord,
    RateLimitState,
)


class RateLimitStore(ABC):
    """Persistencia del estado de rate limiting, indexada por clave de regla+dimensión.

    El estado es opaco para el almacén (``RateLimitState``): quien lo
    interpreta es el algoritmo, no el backend. Eso hace que un mismo
    ``RateLimitStore`` sirva a los cuatro algoritmos sin conocer ninguno.
    """

    @abstractmethod
    async def get(self, key: str) -> RateLimitState | None:
        """Estado actual de ``key``, o ``None`` si no hay ninguno vigente."""
        ...

    @abstractmethod
    async def put(self, key: str, state: RateLimitState, *, ttl_seconds: float) -> None:
        """Guarda ``state`` bajo ``key``, expirándolo pasados ``ttl_seconds``."""
        ...

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Elimina el estado de ``key`` (usado para limpiar límites manualmente)."""
        ...


class QuotaStore(ABC):
    """Persistencia del consumo acumulado de cuotas."""

    @abstractmethod
    async def consume(self, key: str, amount: float, *, ttl_seconds: float) -> float:
        """Suma ``amount`` al consumo de ``key`` y devuelve el total resultante.

        La operación debe ser atómica en implementaciones concurrentes
        (``INCRBYFLOAT`` en Redis) — devolver el total *después* de sumar es
        lo que evita la condición de carrera de "leer, sumar, escribir".
        """
        ...

    @abstractmethod
    async def peek(self, key: str) -> float:
        """Consumo actual de ``key`` sin modificarlo (``0.0`` si no hay ninguno)."""
        ...

    @abstractmethod
    async def release(self, key: str, amount: float) -> float:
        """Resta ``amount`` del consumo de ``key`` — usado por las cuotas de concurrencia."""
        ...

    @abstractmethod
    async def reset(self, key: str) -> None:
        """Elimina el consumo acumulado de ``key``."""
        ...


class IdempotencyStore(ABC):
    """Persistencia de las respuestas ya emitidas para cada ``Idempotency-Key``."""

    @abstractmethod
    async def get(self, key: str) -> IdempotencyRecord | None:
        """Registro vigente de ``key``, o ``None`` si no existe o ya expiró."""
        ...

    @abstractmethod
    async def put(self, record: IdempotencyRecord) -> None:
        """Guarda ``record`` (su propio ``expires_at`` define hasta cuándo es válido)."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Elimina el registro de ``key``."""
        ...


class AuditSink(ABC):
    """Un destino de auditoría de API — dónde acaba cada ``ApiAuditRecord``.

    Deliberadamente separado de ``Exporter`` (``contracts/telemetry.py``):
    la auditoría es un registro de negocio con requisitos de retención y
    cumplimiento propios, no telemetría operativa muestreada — de ahí que
    ``ApiAudit`` nunca aplique muestreo a sus registros (ver ADR-009).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador estable de este destino (p. ej. ``"memory"``, ``"logging"``)."""
        ...

    @abstractmethod
    async def emit(self, record: ApiAuditRecord) -> None:
        """Entrega ``record`` a este destino."""
        ...


class CompressionProvider(ABC):
    """Un algoritmo de compresión de respuestas HTTP."""

    @property
    @abstractmethod
    def algorithm(self) -> CompressionAlgorithm:
        """Codificación que implementa este proveedor."""
        ...

    @property
    @abstractmethod
    def available(self) -> bool:
        """``True`` si el proveedor puede comprimir en este intérprete.

        Existe porque no toda codificación está garantizada por la librería
        estándar: GZip siempre lo está, Brotli requiere un paquete externo
        opcional (ver ``api/compression/providers.py``). Un proveedor no
        disponible se ignora durante la negociación en vez de romper la
        petición.
        """
        ...

    @abstractmethod
    def compress(self, data: bytes) -> bytes:
        """Comprime ``data``."""
        ...


class ApiProtectionPolicy(ABC):
    """Contrato preparado para delegar la protección en un gateway externo.

    Sin implementación concreta en Sprint 2.9 — existe para que integrar
    Azure API Management, Kong o AWS API Gateway consista en implementar
    esta interfaz y pasarla a ``ApiGateway``, sin rediseñar la plataforma
    (criterio de éxito del Sprint, ver ADR-009, "Consecuencias positivas").
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identificador estable de la política (p. ej. ``"azure-apim"``)."""
        ...

    @abstractmethod
    async def evaluate(self, context: object) -> Sequence[str]:
        """Evalúa ``context`` y devuelve los motivos de rechazo (vacío = aceptada)."""
        ...
