"""``SecurityConfiguration`` — configuración del ``SecurityModule``.

Mismo criterio que ``modules/database/configuration.py``: se resuelve
desde un ``Mapping`` (``from_mapping``, típicamente
``ModuleContext.configuration``) y no importa ``config/`` directamente,
para mantener la independencia del resto de ``sdk/``. LDAP y Azure AD no
tienen campos aquí — sus proveedores se construyen aparte (necesitan URIs
de servidor/tenant reales que no tiene sentido "adivinar" con un default)
y se pasan a ``SecurityModule(identity_providers=[...])``.
"""

from __future__ import annotations

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, field


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    if isinstance(value, int):
        return value
    return int(str(value))


def _coerce_str(value: object, default: str) -> str:
    return default if value is None else str(value)


@dataclass(frozen=True, slots=True)
class SecurityConfiguration:
    """Configuración de JWT, API Keys, hashing de contraseñas y catálogo de roles."""

    #: Sin valor por defecto fijo a propósito: uno generado aleatoriamente por
    #: instancia permite que ``SecurityModule()`` funcione de inmediato (igual
    #: ergonomía que ``DatabaseModule()`` con SQLite en memoria) sin nunca
    #: exponer un secreto predecible — producción debe fijar uno explícito y
    #: estable entre reinicios/instancias (ver ``SecuritySettings``).
    jwt_secret: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "teaf"
    jwt_audience: str = "teaf"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 1_209_600
    clock_skew_seconds: int = 30

    api_key_hash_secret: str | None = None
    api_key_header: str = "X-API-Key"
    api_key_query_param: str = "api_key"

    #: ``"argon2"`` (por defecto, recomendación OWASP) o ``"bcrypt"``.
    password_hasher: str = "argon2"

    #: Catálogo de roles: nombre de rol -> conjunto de permisos que otorga.
    roles: Mapping[str, frozenset[str]] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, values: Mapping[str, object]) -> SecurityConfiguration:
        """Construye la configuración desde un ``Mapping`` (claves ausentes usan el default)."""
        jwt_secret_value = values.get("jwt_secret")
        jwt_secret = (
            str(jwt_secret_value) if jwt_secret_value is not None else secrets.token_urlsafe(32)
        )
        api_key_hash_secret = values.get("api_key_hash_secret")
        roles_value = values.get("roles")
        return cls(
            jwt_secret=jwt_secret,
            jwt_algorithm=_coerce_str(values.get("jwt_algorithm"), "HS256"),
            jwt_issuer=_coerce_str(values.get("jwt_issuer"), "teaf"),
            jwt_audience=_coerce_str(values.get("jwt_audience"), "teaf"),
            access_token_ttl_seconds=_coerce_int(values.get("access_token_ttl_seconds"), 900),
            refresh_token_ttl_seconds=_coerce_int(
                values.get("refresh_token_ttl_seconds"), 1_209_600
            ),
            clock_skew_seconds=_coerce_int(values.get("clock_skew_seconds"), 30),
            api_key_hash_secret=(
                str(api_key_hash_secret) if api_key_hash_secret is not None else None
            ),
            api_key_header=_coerce_str(values.get("api_key_header"), "X-API-Key"),
            api_key_query_param=_coerce_str(values.get("api_key_query_param"), "api_key"),
            password_hasher=_coerce_str(values.get("password_hasher"), "argon2"),
            roles=roles_value if isinstance(roles_value, Mapping) else {},
        )
