"""``JWTTokenProvider`` — implementación de ``TokenProvider`` con JWT (PyJWT).

Access token de vida corta + refresh token de vida larga, con revocación
explícita y **rotación con revocación-en-reutilización**: cada llamada a
``refresh()`` revoca el refresh token usado antes de emitir el par nuevo —
si alguien reutiliza un refresh token ya canjeado (p. ej. uno robado),
``refresh()`` falla con ``TokenRevokedException`` (ver
docs/standards/SECURITY-STANDARD.md, sección 1).
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from typing import Any

import jwt as pyjwt

from teaf._internal.contracts.security import TokenProvider
from teaf._internal.core.exceptions import ConfigurationException
from teaf._internal.security.exceptions import (
    TokenException,
    TokenExpiredException,
    TokenRevokedException,
)
from teaf._internal.security.models import Claims, Identity, TokenPair
from teaf._internal.security.tokens.jwt_policy import describe_secret_violation

_ACCESS_TYPE = "access"
_REFRESH_TYPE = "refresh"


class TokenRevocationStore(ABC):
    """Dónde vive la lista de tokens revocados — en memoria por defecto.

    Una aplicación con múltiples instancias debe sustituir
    ``InMemoryTokenRevocationStore`` por una implementación respaldada en
    Redis/base de datos compartida — mismo contrato, sin cambiar
    ``JWTTokenProvider`` (Cloud Ready, ver ADR-005).
    """

    @abstractmethod
    def is_revoked(self, jti: str) -> bool:
        """``True`` si el token con este ``jti`` fue revocado."""
        ...

    @abstractmethod
    def revoke(self, jti: str, *, expires_at: float) -> None:
        """Marca ``jti`` como revocado hasta ``expires_at`` (epoch, segundos)."""
        ...


class InMemoryTokenRevocationStore(TokenRevocationStore):
    """Almacén de revocación en memoria de proceso — suficiente para una sola instancia."""

    def __init__(self) -> None:
        self._revoked: dict[str, float] = {}

    def is_revoked(self, jti: str) -> bool:
        self._evict_expired()
        return jti in self._revoked

    def revoke(self, jti: str, *, expires_at: float) -> None:
        self._revoked[jti] = expires_at

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [jti for jti, expires_at in self._revoked.items() if expires_at < now]
        for jti in expired:
            del self._revoked[jti]


class JWTTokenProvider(TokenProvider):
    """Emite/verifica/refresca/revoca JWT — access + refresh tokens."""

    def __init__(
        self,
        *,
        secret: str,
        algorithm: str = "HS256",
        issuer: str = "teaf",
        audience: str = "teaf",
        access_token_ttl_seconds: int = 900,
        refresh_token_ttl_seconds: int = 1_209_600,
        clock_skew_seconds: int = 30,
        revocation_store: TokenRevocationStore | None = None,
    ) -> None:
        """``access_token_ttl_seconds``/``refresh_token_ttl_seconds`` por defecto son
        15 minutos / 14 días (recomendación de SECURITY-STANDARD.md, sección 1).
        ``clock_skew_seconds`` tolera diferencias de reloj entre instancias al
        validar ``exp``/``nbf``. ``algorithm`` acepta cualquiera soportado por
        PyJWT (``HS256`` con ``secret`` simétrico, ``RS256``/``ES256`` con
        ``secret`` como clave privada/pública PEM).

        Desde Sprint 3.0 el secreto se valida **aquí, al construir**, contra
        la longitud mínima que exige RFC 7518 §3.2 para el algoritmo elegido
        (ver ``jwt_policy``). Es deliberado que falle en la construcción y no
        al firmar: un secreto débil es un error de despliegue, y descubrirlo
        en la primera petición autenticada —en producción— es demasiado
        tarde. Solo aplica a los algoritmos HMAC; para claves PEM no hay
        longitud mínima que medir.
        """
        violation = describe_secret_violation(secret, algorithm)
        if violation is not None:
            raise ConfigurationException(violation)

        self._secret = secret
        self._algorithm = algorithm
        self._issuer = issuer
        self._audience = audience
        self._access_ttl = access_token_ttl_seconds
        self._refresh_ttl = refresh_token_ttl_seconds
        self._clock_skew = clock_skew_seconds
        self._revocation_store: TokenRevocationStore = (
            revocation_store or InMemoryTokenRevocationStore()
        )

    def _encode(
        self, identity: Identity, *, token_type: str, ttl: int, tenant_id: str | None
    ) -> str:
        now = int(time.time())
        claims = identity.claims
        payload: dict[str, Any] = {
            "sub": identity.id,
            "iss": self._issuer,
            "aud": self._audience,
            "iat": now,
            "nbf": now,
            "exp": now + ttl,
            "jti": str(uuid.uuid4()),
            "type": token_type,
            "providerId": identity.provider_id,
            "name": claims.name,
            "email": claims.email,
            "tenant": tenant_id or claims.tenant,
            "roles": sorted(claims.roles),
            "permissions": sorted(claims.permissions),
            "groups": sorted(claims.groups),
            "locale": claims.locale,
            "timezone": claims.timezone,
            "department": claims.department,
            "jobTitle": claims.job_title,
        }
        encoded: str = pyjwt.encode(payload, self._secret, algorithm=self._algorithm)
        return encoded

    async def issue(self, identity: Identity, *, tenant_id: str | None = None) -> TokenPair:
        """Emite un ``TokenPair`` nuevo para ``identity``."""
        access_token = self._encode(
            identity, token_type=_ACCESS_TYPE, ttl=self._access_ttl, tenant_id=tenant_id
        )
        refresh_token = self._encode(
            identity, token_type=_REFRESH_TYPE, ttl=self._refresh_ttl, tenant_id=tenant_id
        )
        return TokenPair(
            access_token=access_token, refresh_token=refresh_token, expires_in=self._access_ttl
        )

    def _decode(self, token: str, *, expected_type: str) -> dict[str, Any]:
        try:
            payload: dict[str, Any] = pyjwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._clock_skew,
            )
        except pyjwt.ExpiredSignatureError as exc:
            raise TokenExpiredException("El token expiró.") from exc
        except pyjwt.InvalidTokenError as exc:
            raise TokenException(f"Token inválido: {exc}") from exc

        if payload.get("type") != expected_type:
            raise TokenException(f"Se esperaba un token de tipo '{expected_type}'.")
        jti = payload.get("jti")
        if jti and self._revocation_store.is_revoked(jti):
            raise TokenRevokedException("El token fue revocado.")
        return payload

    @staticmethod
    def _payload_to_identity(payload: dict[str, Any]) -> Identity:
        claims = Claims(
            sub=payload["sub"],
            name=payload.get("name"),
            email=payload.get("email"),
            tenant=payload.get("tenant"),
            roles=frozenset(payload.get("roles") or ()),
            permissions=frozenset(payload.get("permissions") or ()),
            groups=frozenset(payload.get("groups") or ()),
            locale=payload.get("locale"),
            timezone=payload.get("timezone"),
            department=payload.get("department"),
            job_title=payload.get("jobTitle"),
        )
        return Identity(
            id=payload["sub"], provider_id=payload.get("providerId", "jwt"), claims=claims
        )

    async def verify(self, token: str) -> Identity:
        """Verifica un access token y devuelve la identidad que representa."""
        payload = self._decode(token, expected_type=_ACCESS_TYPE)
        return self._payload_to_identity(payload)

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Canjea ``refresh_token`` por un ``TokenPair`` nuevo, revocando el usado."""
        payload = self._decode(refresh_token, expected_type=_REFRESH_TYPE)
        identity = self._payload_to_identity(payload)
        jti = payload.get("jti")
        if jti:
            self._revocation_store.revoke(jti, expires_at=float(payload["exp"]))
        return await self.issue(identity, tenant_id=payload.get("tenant"))

    async def revoke(self, token: str) -> None:
        """Revoca ``token`` (access o refresh) — deja de ser válido de inmediato.

        Decodifica ignorando ``exp`` (``verify_exp=False``) porque un token
        ya expirado también debe poder revocarse sin error, por simetría y
        para no dejar huecos si el llamador no sabe si aún es válido.
        """
        try:
            payload = pyjwt.decode(
                token,
                self._secret,
                algorithms=[self._algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._clock_skew,
                options={"verify_exp": False},
            )
        except pyjwt.InvalidTokenError as exc:
            raise TokenException(f"Token inválido: {exc}") from exc
        jti = payload.get("jti")
        if jti:
            self._revocation_store.revoke(jti, expires_at=float(payload.get("exp", time.time())))
