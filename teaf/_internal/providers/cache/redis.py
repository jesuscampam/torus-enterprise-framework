"""``RedisCacheProvider`` — caché distribuida sobre Redis (Sprint 3.0, ADR-012).

Es la pieza que permite que varias réplicas compartan estado: sin ella, un
límite de 100 peticiones por minuto con 4 réplicas son 400 en la práctica,
porque cada proceso lleva su propia cuenta.

**El import de ``redis`` es perezoso, dentro de ``connect()``.** No es un
detalle de estilo: importar el módulo en la cabecera obligaría a instalar
``redis`` para *importar* TEAF, y entonces la dependencia no sería opcional
por mucho que se declare como extra. Construir el proveedor sin el paquete
instalado tampoco falla — solo falla al conectar, que es cuando de verdad
hace falta, y con un mensaje que dice qué instalar.

Sobre los tipos: ``redis`` no está instalado en el entorno de tipado, así
que el cliente se maneja como ``Any``. Es la misma decisión que toma
``sqlalchemy_provider.py`` con las partes no tipadas de SQLAlchemy, y queda
acotada a este archivo: hacia fuera solo se ve el contrato ``CacheProvider``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from teaf._internal.contracts.cache import CacheProvider
from teaf._internal.core.exceptions import ConfigurationException, InfrastructureException

_MISSING_DEPENDENCY = (
    "El proveedor de caché Redis necesita el paquete 'redis', que es un extra opcional "
    "de TEAF. Instálelo con 'pip install teaf[redis]' — o use InMemoryCacheProvider si "
    "la aplicación corre en una sola instancia (ver docs/modules/cache/CACHE.md)."
)


@dataclass(frozen=True, slots=True)
class RedisCacheConfiguration:
    """Parámetros de conexión. Ningún valor sensible se fija en código.

    ``url`` admite la forma estándar ``redis://`` o ``rediss://`` (TLS) e
    incluye credenciales cuando el despliegue las use; por eso debe venir de
    una variable de entorno o de un gestor de secretos, nunca del
    repositorio (ver SECURITY-STANDARD.md §9).
    """

    url: str = "redis://localhost:6379/0"
    #: Prefijo de todas las claves. Permite compartir una instancia de Redis
    #: entre aplicaciones sin que se pisen las claves entre sí.
    key_prefix: str = "teaf"
    #: Segundos para abrir la conexión y para cada operación. Un límite
    #: explícito evita que un Redis caído cuelgue las peticiones en vez de
    #: fallar rápido.
    connect_timeout_seconds: float = 5.0
    operation_timeout_seconds: float = 5.0
    #: Conexiones máximas del pool.
    max_connections: int = 10
    #: Verificación del certificado cuando la URL es ``rediss://``.
    #: Desactivarla solo tiene sentido contra un Redis de desarrollo con
    #: certificado autofirmado, y deja la conexión expuesta a un intermediario.
    tls_verify: bool = True

    def validated(self) -> RedisCacheConfiguration:
        """Comprueba lo que se puede comprobar sin abrir una conexión."""
        if not self.url.strip():
            raise ConfigurationException("La URL de Redis no puede estar vacía.")
        if not self.url.startswith(("redis://", "rediss://", "unix://")):
            raise ConfigurationException(
                f"URL de Redis no reconocida: {self.url!r}. "
                "Debe empezar por 'redis://', 'rediss://' (TLS) o 'unix://'."
            )
        if self.max_connections < 1:
            raise ConfigurationException("'max_connections' debe ser al menos 1.")
        return self


class RedisCacheProvider(CacheProvider):
    """``CacheProvider`` respaldado por Redis."""

    def __init__(self, configuration: RedisCacheConfiguration | None = None) -> None:
        """No abre ninguna conexión: solo valida la configuración.

        Construir es barato y sin efectos, igual que en ``DatabaseModule``.
        La conexión se abre en ``connect()``, que el ciclo de vida del módulo
        llama en ``start()``.
        """
        self.configuration = (configuration or RedisCacheConfiguration()).validated()
        self._client: Any | None = None

    @property
    def uses_tls(self) -> bool:
        """``True`` si la URL pide TLS (``rediss://``).

        Determina qué opciones acepta el pool: ``tls_verify`` solo tiene
        sentido —y solo se puede pasar— sobre una conexión TLS.
        """
        return self.configuration.url.startswith("rediss://")

    def key(self, key: str) -> str:
        """Clave con el prefijo aplicado."""
        prefix = self.configuration.key_prefix
        return f"{prefix}:{key}" if prefix else key

    # -- Ciclo de vida ---------------------------------------------------------------------

    async def connect(self) -> None:
        """Crea el pool. Idempotente: reconectar sobre un pool abierto no hace nada."""
        if self._client is not None:
            return
        try:
            # El aislamiento de tipos de ``redis`` está en pyproject.toml
            # ([[tool.mypy.overrides]]) — ver el docstring del módulo.
            import redis.asyncio as redis_asyncio  # noqa: PLC0415
        except ImportError as exc:
            raise ConfigurationException(_MISSING_DEPENDENCY) from exc

        config = self.configuration
        options: dict[str, Any] = {
            "max_connections": config.max_connections,
            "socket_connect_timeout": config.connect_timeout_seconds,
            "socket_timeout": config.operation_timeout_seconds,
        }
        # ``ssl_cert_reqs`` solo lo entiende ``SSLConnection``: pasarlo sobre
        # una URL ``redis://`` revienta con ``TypeError`` en la primera
        # operación, no al conectar (``from_url`` es perezoso). Por eso la
        # opción se añade únicamente cuando la conexión es TLS.
        if self.uses_tls:
            options["ssl_cert_reqs"] = "required" if config.tls_verify else "none"
        # ``from_url`` está sin anotar dentro de un paquete que sí declara
        # ``py.typed``, así que mypy la rechaza como llamada no tipada. Pasar
        # por una referencia ``Any`` mantiene el aislamiento de tipos que
        # describe el docstring del módulo y hace que la comprobación dé el
        # mismo resultado esté o no instalado el extra.
        from_url: Any = redis_asyncio.from_url
        self._client = from_url(config.url, **options)

    async def disconnect(self) -> None:
        """Cierra el pool y suelta el cliente. Idempotente."""
        client, self._client = self._client, None
        if client is not None:
            await client.aclose()

    def _require_client(self) -> Any:
        if self._client is None:
            raise InfrastructureException(
                "El proveedor de caché Redis no está conectado: llame a connect() antes "
                "de operar (el ciclo de vida del módulo lo hace en start())."
            )
        return self._client

    # -- Operaciones -----------------------------------------------------------------------

    async def get(self, key: str) -> bytes | None:
        value: bytes | None = await self._require_client().get(self.key(key))
        return value

    async def set(self, key: str, value: bytes, *, ttl_seconds: float | None = None) -> None:
        client = self._require_client()
        if ttl_seconds is None:
            await client.set(self.key(key), value)
            return
        # ``PSETEX`` trabaja en milisegundos; se redondea hacia arriba para no
        # acortar nunca un TTL por truncamiento. Un TTL <= 0 no se puede
        # expresar en Redis, así que se traduce a borrar la clave — que es lo
        # que significa "ya expirado".
        millis = max(int(ttl_seconds * 1000 + 0.999), 0)
        if millis <= 0:
            await client.delete(self.key(key))
            return
        await client.set(self.key(key), value, px=millis)

    async def delete(self, key: str) -> bool:
        removed: int = await self._require_client().delete(self.key(key))
        return removed > 0

    async def ttl(self, key: str) -> float | None:
        """Traduce la respuesta de ``PTTL`` al contrato.

        Redis devuelve ``-2`` si la clave no existe y ``-1`` si existe sin
        expiración; el contrato une ambos casos en ``None``.
        """
        millis: int = await self._require_client().pttl(self.key(key))
        return millis / 1000 if millis >= 0 else None

    async def ping(self) -> bool:
        try:
            return bool(await self._require_client().ping())
        except Exception:  # noqa: BLE001 — cualquier fallo aquí significa "no responde"
            return False

    async def health_check(self) -> bool:
        """``False`` en vez de excepción si no hay conexión.

        Un health check que lanza no informa: convierte «Redis no está
        disponible» en «la comprobación de salud está rota», y son cosas
        distintas.
        """
        if self._client is None:
            return False
        return await self.ping()
