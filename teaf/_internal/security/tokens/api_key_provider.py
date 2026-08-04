"""``ApiKeyProvider`` — emisión, verificación, revocación, scopes y rotación de API Keys.

La clave en texto plano se genera una sola vez (al emitirla) y nunca se
almacena ni se puede recuperar — solo su hash (HMAC-SHA256 con un secreto
del servidor, no Argon2/BCrypt: una API Key ya es de alta entropía
aleatoria, no una contraseña humana de baja entropía que necesite un hash
lento). El transporte (header/query string/header personalizado) es
responsabilidad de ``identity_providers/api_key.py`` — este módulo es
agnóstico de HTTP.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta

from teaf._internal.security.exceptions import ApiKeyException


@dataclass(frozen=True, slots=True)
class ApiKeyRecord:
    """Metadata persistida de una API Key — nunca contiene la clave en texto plano."""

    id: str
    hashed_key: str
    principal_id: str
    scopes: frozenset[str] = field(default_factory=frozenset)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    revoked: bool = False
    last_rotated_at: datetime | None = None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """``True`` si ``expires_at`` está fijado y ya pasó."""
        if self.expires_at is None:
            return False
        return (now or datetime.now(UTC)) >= self.expires_at

    def is_valid(self, *, now: datetime | None = None) -> bool:
        """``True`` si no está revocada ni expirada."""
        return not self.revoked and not self.is_expired(now=now)

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) — nunca incluye ``hashed_key``."""
        return {
            "id": self.id,
            "principalId": self.principal_id,
            "scopes": sorted(self.scopes),
            "createdAt": self.created_at.isoformat(),
            "expiresAt": self.expires_at.isoformat() if self.expires_at else None,
            "revoked": self.revoked,
            "lastRotatedAt": self.last_rotated_at.isoformat() if self.last_rotated_at else None,
        }


class ApiKeyStore(ABC):
    """Persistencia de ``ApiKeyRecord`` — en memoria por defecto, sustituible por una
    implementación respaldada en base de datos sin cambiar ``ApiKeyProvider``."""

    @abstractmethod
    def save(self, record: ApiKeyRecord) -> None:
        """Crea o actualiza ``record`` (identificado por ``record.id``)."""
        ...

    @abstractmethod
    def get(self, key_id: str) -> ApiKeyRecord | None:
        """Devuelve el registro con ``key_id``, o ``None`` si no existe."""
        ...

    @abstractmethod
    def find_by_hash(self, hashed_key: str) -> ApiKeyRecord | None:
        """Devuelve el registro cuyo ``hashed_key`` coincide, o ``None``."""
        ...

    @abstractmethod
    def list_for_principal(self, principal_id: str) -> tuple[ApiKeyRecord, ...]:
        """Todas las API Keys emitidas para ``principal_id``."""
        ...


class InMemoryApiKeyStore(ApiKeyStore):
    """Almacén en memoria de proceso — suficiente para una sola instancia o pruebas."""

    def __init__(self) -> None:
        self._by_id: dict[str, ApiKeyRecord] = {}
        self._by_hash: dict[str, str] = {}

    def save(self, record: ApiKeyRecord) -> None:
        self._by_id[record.id] = record
        self._by_hash[record.hashed_key] = record.id

    def get(self, key_id: str) -> ApiKeyRecord | None:
        return self._by_id.get(key_id)

    def find_by_hash(self, hashed_key: str) -> ApiKeyRecord | None:
        key_id = self._by_hash.get(hashed_key)
        return self._by_id.get(key_id) if key_id else None

    def list_for_principal(self, principal_id: str) -> tuple[ApiKeyRecord, ...]:
        return tuple(r for r in self._by_id.values() if r.principal_id == principal_id)


class ApiKeyProvider:
    """Emite, verifica, revoca y rota API Keys — transporte-agnóstico."""

    def __init__(self, *, secret: str, store: ApiKeyStore | None = None) -> None:
        """``secret`` es el pepper del servidor (nunca viaja con la key) usado para
        hashear con HMAC-SHA256 antes de guardar/comparar — ver
        ``SecuritySettings.api_key_hash_secret``."""
        self._secret = secret.encode("utf-8")
        self._store = store or InMemoryApiKeyStore()

    def _hash(self, raw_key: str) -> str:
        return hmac.new(self._secret, raw_key.encode("utf-8"), hashlib.sha256).hexdigest()

    def issue(
        self,
        *,
        principal_id: str,
        scopes: frozenset[str] = frozenset(),
        ttl: timedelta | None = None,
    ) -> tuple[str, ApiKeyRecord]:
        """Emite una API Key nueva. Devuelve ``(raw_key, record)`` — ``raw_key`` es la
        única vez que la clave en texto plano existe fuera del cliente; el llamador
        debe mostrarla una sola vez y descartarla."""
        raw_key = f"teaf_{secrets.token_urlsafe(32)}"
        now = datetime.now(UTC)
        record = ApiKeyRecord(
            id=str(uuid.uuid4()),
            hashed_key=self._hash(raw_key),
            principal_id=principal_id,
            scopes=scopes,
            created_at=now,
            expires_at=(now + ttl) if ttl else None,
        )
        self._store.save(record)
        return raw_key, record

    def verify(self, raw_key: str, *, required_scope: str | None = None) -> ApiKeyRecord:
        """Verifica ``raw_key`` y devuelve su registro.

        Lanza ``ApiKeyException`` si no existe, está revocada, expiró, o
        (cuando se pasa ``required_scope``) no incluye ese scope.
        """
        record = self._store.find_by_hash(self._hash(raw_key))
        if record is None:
            raise ApiKeyException("API Key inválida.")
        if not record.is_valid():
            raise ApiKeyException("API Key expirada o revocada.")
        if required_scope is not None and required_scope not in record.scopes:
            raise ApiKeyException(f"API Key sin el scope requerido '{required_scope}'.")
        return record

    def revoke(self, key_id: str) -> None:
        """Revoca la API Key ``key_id`` — deja de ser válida de inmediato."""
        record = self._store.get(key_id)
        if record is None:
            raise ApiKeyException(f"API Key '{key_id}' no encontrada.")
        self._store.save(replace(record, revoked=True))

    def rotate(self, key_id: str) -> str:
        """Revoca ``key_id`` y emite una API Key nueva con el mismo principal/scopes.

        Devuelve la nueva clave en texto plano (única vez visible).
        """
        record = self._store.get(key_id)
        if record is None:
            raise ApiKeyException(f"API Key '{key_id}' no encontrada.")
        self.revoke(key_id)
        raw_key, new_record = self.issue(principal_id=record.principal_id, scopes=record.scopes)
        self._store.save(replace(new_record, last_rotated_at=datetime.now(UTC)))
        return raw_key
