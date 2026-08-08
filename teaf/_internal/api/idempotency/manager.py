"""``IdempotencyManager`` — reproducción segura de peticiones repetidas (Sprint 2.9).

El problema que resuelve: un cliente envía ``POST /orders``, la respuesta se
pierde por un corte de red y el cliente reintenta. Sin idempotencia, se
crean dos pedidos. Con ella, el segundo intento devuelve *exactamente* la
respuesta del primero, sin volver a ejecutar el endpoint.

Tres reglas, todas necesarias para que eso sea correcto:

1. **La clave la pone el cliente** (``Idempotency-Key``). Solo él sabe qué
   dos peticiones son "la misma intención de negocio".
2. **La huella la pone el servidor.** Reutilizar una clave con un cuerpo
   distinto no es un reintento, es un error del cliente — y devolver la
   respuesta antigua ocultaría el fallo. De ahí
   ``IdempotencyConflictException`` (HTTP 409).
3. **Solo se guardan respuestas de éxito.** Cachear un 500 condenaría al
   cliente a recibir ese mismo error durante todo el TTL, incluso cuando la
   causa ya se hubiera resuelto.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Mapping

from teaf._internal.api.exceptions import IdempotencyConflictException
from teaf._internal.api.models import IdempotencyRecord
from teaf._internal.api.providers.memory import Clock, InMemoryIdempotencyStore
from teaf._internal.contracts.api import IdempotencyStore

#: Métodos para los que tiene sentido la idempotencia gestionada. GET/PUT/
#: DELETE ya son idempotentes por definición de HTTP; POST y PATCH no lo son,
#: y son exactamente los que necesitan esta protección.
DEFAULT_IDEMPOTENT_METHODS: tuple[str, ...] = ("POST", "PATCH")


def build_fingerprint(*, method: str, path: str, body: bytes) -> str:
    """Huella SHA-256 de la petición — método, ruta y cuerpo.

    Se usa SHA-256 y no un hash rápido no criptográfico porque una colisión
    aquí significaría devolver la respuesta de *otra* petición: el coste de
    calcularlo es irrelevante comparado con esa consecuencia.
    """
    digest = hashlib.sha256()
    digest.update(method.upper().encode("utf-8"))
    digest.update(b"\0")
    digest.update(path.encode("utf-8"))
    digest.update(b"\0")
    digest.update(body)
    return digest.hexdigest()


class IdempotencyManager:
    """Detecta reintentos, reproduce respuestas y bloquea reutilizaciones incorrectas."""

    def __init__(
        self,
        *,
        store: IdempotencyStore | None = None,
        ttl_seconds: float = 86_400.0,
        methods: tuple[str, ...] = DEFAULT_IDEMPOTENT_METHODS,
        header_name: str = "Idempotency-Key",
        clock: Clock = time.time,
        enabled: bool = True,
    ) -> None:
        self._store = store if store is not None else InMemoryIdempotencyStore(clock=clock)
        self._ttl_seconds = ttl_seconds
        self._methods = tuple(m.upper() for m in methods)
        self._header_name = header_name
        self._clock = clock
        self._enabled = enabled

    @property
    def enabled(self) -> bool:
        """``False`` desactiva la idempotencia sin desmontar el middleware."""
        return self._enabled

    @property
    def header_name(self) -> str:
        """Cabecera de la que se lee la clave de idempotencia."""
        return self._header_name

    @property
    def ttl_seconds(self) -> float:
        """Cuánto tiempo se conserva una respuesta para poder reproducirla."""
        return self._ttl_seconds

    @property
    def store(self) -> IdempotencyStore:
        """Almacén de respuestas idempotentes."""
        return self._store

    def applies_to(self, method: str) -> bool:
        """``True`` si ``method`` está sujeto a idempotencia gestionada."""
        return self._enabled and method.upper() in self._methods

    async def lookup(self, key: str, *, fingerprint: str) -> IdempotencyRecord | None:
        """Busca una respuesta ya emitida para ``key``.

        Returns:
            El registro a reproducir, o ``None`` si es la primera vez que se
            ve esta clave (o si ya expiró).

        Raises:
            IdempotencyConflictException: ``key`` ya se usó con una petición
                distinta (``fingerprint`` no coincide).
        """
        record = await self._store.get(key)
        if record is None:
            return None
        if record.fingerprint != fingerprint:
            raise IdempotencyConflictException(
                f"La clave de idempotencia '{key}' ya se usó con una petición distinta. "
                "Usa una clave nueva para una petición nueva."
            )
        return record

    async def remember(
        self,
        key: str,
        *,
        fingerprint: str,
        status_code: int,
        body: bytes,
        headers: Mapping[str, str] | None = None,
    ) -> IdempotencyRecord | None:
        """Guarda la respuesta de ``key`` para poder reproducirla.

        No guarda nada (y devuelve ``None``) para respuestas de error 5xx —
        ver la regla 3 del docstring del módulo.
        """
        if status_code >= 500:
            return None
        now = self._clock()
        record = IdempotencyRecord(
            key=key,
            fingerprint=fingerprint,
            status_code=status_code,
            body=body,
            headers=dict(headers or {}),
            created_at=now,
            expires_at=now + self._ttl_seconds,
        )
        await self._store.put(record)
        return record

    async def forget(self, key: str) -> None:
        """Elimina la respuesta guardada de ``key``."""
        await self._store.delete(key)
