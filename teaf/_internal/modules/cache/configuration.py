"""``CacheConfiguration`` — configuración del módulo de caché (Sprint 3.0).

Mismo criterio que ``DatabaseConfiguration``: un objeto de configuración
propio del módulo, desacoplado de ``config/settings.py``, que una aplicación
puede construir a mano o derivar de sus ``Settings`` con ``from_mapping``.

El backend por defecto es ``memory``, y eso es una decisión, no una
casualidad: TEAF debe funcionar sin infraestructura desplegada. Redis se
activa configurándolo explícitamente.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from teaf._internal.core.exceptions import ConfigurationException
from teaf._internal.providers.cache.redis import RedisCacheConfiguration


class CacheBackend(str, Enum):
    """Implementación de ``CacheProvider`` que usa el módulo."""

    MEMORY = "memory"
    REDIS = "redis"


def _coerce_bool(value: object, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _coerce_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def _coerce_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class CacheConfiguration:
    """Configuración del módulo de caché."""

    enabled: bool = False
    backend: CacheBackend = CacheBackend.MEMORY
    redis: RedisCacheConfiguration = field(default_factory=RedisCacheConfiguration)

    @classmethod
    def from_mapping(cls, values: dict[str, object]) -> CacheConfiguration:
        """Construye la configuración desde un mapa plano — típicamente ``Settings.model_dump()``.

        Reconoce el prefijo ``cache_`` igual que ``ApiProtectionConfiguration``
        reconoce ``api_``, de modo que ``from_mapping(settings.model_dump())``
        funciona sin transformar nada.
        """

        def _get(key: str) -> object:
            return values.get(f"cache_{key}", values.get(key))

        backend_raw = str(_get("backend") or CacheBackend.MEMORY.value).strip().lower()
        try:
            backend = CacheBackend(backend_raw)
        except ValueError as exc:
            opciones = ", ".join(b.value for b in CacheBackend)
            raise ConfigurationException(
                f"Backend de caché desconocido: {backend_raw!r}. Opciones: {opciones}."
            ) from exc

        defaults = RedisCacheConfiguration()
        return cls(
            enabled=_coerce_bool(_get("enabled"), False),
            backend=backend,
            redis=RedisCacheConfiguration(
                url=str(_get("redis_url") or defaults.url),
                key_prefix=str(_get("key_prefix") or defaults.key_prefix),
                connect_timeout_seconds=_coerce_float(
                    _get("connect_timeout_seconds"), defaults.connect_timeout_seconds
                ),
                operation_timeout_seconds=_coerce_float(
                    _get("operation_timeout_seconds"), defaults.operation_timeout_seconds
                ),
                max_connections=_coerce_int(_get("max_connections"), defaults.max_connections),
                tls_verify=_coerce_bool(_get("tls_verify"), defaults.tls_verify),
            ),
        )
