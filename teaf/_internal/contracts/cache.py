"""Contrato de proveedor de caché distribuida (Sprint 3.0, ADR-012).

Abstrae un almacén clave-valor con expiración detrás de una interfaz
independiente del motor concreto, igual que ``DatabaseProvider`` hace con el
ORM. El núcleo del framework nunca conoce Redis:

    Core → CacheProvider (este contrato) → RedisCacheProvider → redis-py

Deliberadamente **mínimo**. Un envoltorio completo de Redis —listas,
conjuntos ordenados, streams, scripts Lua— sería una librería distinta y no
la necesita nada de lo que TEAF hace hoy. Las seis operaciones de aquí son
exactamente las que consumen los almacenes de rate limiting, cuotas e
idempotencia (``teaf/_internal/api/providers/redis.py``), y ampliarlo se
hace cuando exista un caso real, no antes ([CLAUDE.md](../../../CLAUDE.md)
§3).

No se confunde con ``StorageProvider`` (``contracts/storage.py``): aquel es
almacenamiento de objetos —subir y descargar ficheros por ruta— y no tiene
expiración. Son problemas distintos y por eso son contratos distintos.

Las cuatro primeras operaciones (``connect``/``disconnect``/``health_check``
y el ciclo de vida que implican) tienen la misma forma que
``DatabaseProvider`` a propósito: un proveedor de infraestructura de TEAF se
arranca y se apaga siempre igual, así que quien conozca uno conoce el otro.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class CacheProvider(ABC):
    """Almacén clave-valor con expiración, y su ciclo de vida."""

    @abstractmethod
    async def connect(self) -> None:
        """Abre el pool de conexiones. Idempotente si ya está conectado."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Cierra el pool de forma ordenada. Idempotente si ya está cerrado.

        Debe liberar **todas** las conexiones: un pool que sobrevive al
        apagado es una fuga de recursos que solo se manifiesta al reiniciar
        muchas veces, que es justo cuando peor se diagnostica.
        """
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        """Valor de ``key``, o ``None`` si no existe o ya expiró.

        Devuelve ``bytes`` y no ``str`` porque el almacén no debe interpretar
        lo que guarda: la serialización es responsabilidad de quien llama.
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: bytes, *, ttl_seconds: float | None = None) -> None:
        """Guarda ``value`` en ``key``, opcionalmente con expiración.

        ``ttl_seconds=None`` guarda sin expiración. Un TTL menor o igual que
        cero se trata como "expira de inmediato", no como "sin expiración":
        confundir ambos convierte un dato efímero en uno permanente.
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Borra ``key``. ``True`` si existía, ``False`` si no había nada que borrar."""
        ...

    @abstractmethod
    async def ttl(self, key: str) -> float | None:
        """Segundos que le quedan a ``key``.

        ``None`` si la clave no existe **o** si existe sin expiración — dos
        situaciones que ninguna de las operaciones de TEAF necesita
        distinguir. Si algún día hiciera falta, se distinguen combinando con
        ``get``.
        """
        ...

    @abstractmethod
    async def ping(self) -> bool:
        """``True`` si el almacén responde. Base del health check."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """``True`` si el proveedor está operativo — misma forma que ``DatabaseProvider``.

        Se separa de ``ping`` porque un proveedor puede querer comprobar algo
        más que la conectividad (p. ej. que el pool no esté agotado) sin
        cambiar el significado de ``ping``.
        """
        ...
