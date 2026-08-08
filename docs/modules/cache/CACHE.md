# Cache Module — TEAF

Documentación del Sprint 3.0 (Production Infrastructure & Runtime Modernization, v0.10.0-alpha):
el quinto módulo oficial construido sobre el [Module SDK](../../sdk/SDK.md). Almacén clave-valor
con expiración, en memoria o sobre Redis, con ciclo de vida y health check. Decisión de
arquitectura y justificación de la dependencia:
[ADR-012](../../architecture/adr/ADR-012-redis-optional-infrastructure.md).

> Ninguna clave ni política de negocio se define aquí. Este módulo es infraestructura pura: el
> «cómo» compartir estado, nunca el «qué» se guarda.

## 1. Para qué existe

Los almacenes en memoria de la [plataforma de protección de APIs](../../api/API-PROTECTION.md) son
**por proceso**. Con 4 réplicas:

| Control | Con almacén en memoria | Con almacén compartido |
|---|---|---|
| Rate limiting «100 req/min» | 400 req/min reales (100 por réplica) | 100 req/min reales |
| Cuota «10 000 al día» | 40 000 al día | 10 000 al día |
| Idempotencia | Un reintento que caiga en otra réplica **se ejecuta dos veces** | Se reproduce la respuesta original |

Eso es lo que este módulo desbloquea. Si su aplicación corre en **una sola instancia, no necesita
nada de aquí**: el backend por defecto es en memoria y TEAF arranca sin infraestructura desplegada.

## 2. Arquitectura y capas

```
teaf/_internal/contracts/
└── cache.py                        # CacheProvider — el contrato (espejo de DatabaseProvider)

teaf/_internal/providers/cache/     # Implementaciones
├── memory.py                         # InMemoryCacheProvider — por defecto, con purga amortizada
└── redis.py                            # RedisCacheProvider — extra opcional teaf[redis]

teaf/_internal/modules/cache/       # El módulo SDK propiamente dicho
├── configuration.py                  # CacheBackend + CacheConfiguration (from_mapping)
├── health.py                           # CacheHealth (caché síncrona + refresh asíncrono)
├── manifest.py                           # build_cache_manifest() — capacidades/servicios/health
└── module.py                               # CacheModule(ModuleBase) + create_cache_provider()

teaf/_internal/api/providers/redis.py  # Los tres almacenes distribuidos, sobre CacheProvider
```

La regla que ordena todo esto: **`Core → contrato → provider → Redis`**. El núcleo del framework
nunca importa Redis. El módulo elige una implementación según la configuración y la registra en el
contenedor **bajo el contrato**, nunca bajo la clase concreta — quien resuelve `CacheProvider` no
sabe, ni necesita saber, si detrás hay un diccionario o un clúster.

## 3. El contrato

```python
class CacheProvider(ABC):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def set(self, key: str, value: bytes, *, ttl_seconds: float | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...
    async def ttl(self, key: str) -> float | None: ...
    async def ping(self) -> bool: ...
    async def health_check(self) -> bool: ...
```

Tres decisiones que conviene conocer:

- **Los valores son `bytes`**, no `str` ni objetos. Serializar es responsabilidad de quien
  almacena; el contrato no impone JSON ni pickle, y así un cuerpo binario sobrevive intacto.
- **`ttl()` devuelve `None`** tanto si la clave no existe como si existe sin expiración. Redis
  distingue ambos casos (`-2` y `-1`); el contrato los une porque ningún consumidor necesita la
  diferencia.
- **`health_check()` devuelve `False` en vez de lanzar** cuando no hay conexión. Un health check
  que lanza convierte «Redis no está disponible» en «la comprobación de salud está rota», y son
  cosas distintas.

## 4. Uso

Todo lo necesario está en la API pública (`teaf.cache`, reexportado desde `teaf`); no hace falta
tocar `teaf._internal`.

### En memoria — el valor por defecto

```python
from teaf import Application, CacheModule

app = Application(modules=[CacheModule()])
```

### Sobre Redis

```python
from teaf import (
    Application, CacheBackend, CacheConfiguration, CacheModule, RedisCacheConfiguration,
)

configuration = CacheConfiguration(
    backend=CacheBackend.REDIS,
    redis=RedisCacheConfiguration(url="rediss://mi-cache.redis.cache.windows.net:6380/0"),
)
app = Application(modules=[CacheModule(configuration)])
```

### Protección de APIs distribuida

El punto de cableado es un único parámetro:

```python
from teaf import ApiProtectionModule, CacheModule

cache = CacheModule(configuration)
app = Application(modules=[cache, ApiProtectionModule(cache_provider=cache.provider)])
```

Con eso, `RedisRateLimitStore`, `RedisQuotaStore` y `RedisIdempotencyStore` sustituyen a sus
equivalentes en memoria sin que cambie nada más: ni las reglas, ni los middlewares, ni el orden de
la cadena.

## 5. Configuración

Por variables de entorno, con el prefijo `CACHE_` (`CacheConfiguration.from_mapping` las reconoce):

| Variable | Por defecto | Qué hace |
|---|---|---|
| `CACHE_BACKEND` | `memory` | `memory` o `redis` |
| `CACHE_REDIS_URL` | `redis://localhost:6379/0` | `redis://`, `rediss://` (TLS) o `unix://` |
| `CACHE_KEY_PREFIX` | `teaf` | Prefijo de todas las claves — permite compartir una instancia entre aplicaciones |
| `CACHE_CONNECT_TIMEOUT_SECONDS` | `5.0` | Límite para abrir la conexión |
| `CACHE_OPERATION_TIMEOUT_SECONDS` | `5.0` | Límite por operación |
| `CACHE_MAX_CONNECTIONS` | `10` | Tamaño del pool |
| `CACHE_TLS_VERIFY` | `true` | Verificación del certificado (solo aplica a `rediss://`) |

**La URL nunca se escribe en el repositorio.** Suele llevar credenciales, así que va en una
variable de entorno o en un gestor de secretos — ver
[SECURITY-STANDARD.md §9](../../standards/SECURITY-STANDARD.md) y
[SECURITY-CONFIGURATION.md](../../security/SECURITY-CONFIGURATION.md).

`tls_verify=False` solo tiene sentido contra un Redis de desarrollo con certificado autofirmado, y
deja la conexión expuesta a un intermediario.

## 6. Instalación del extra

```bash
pip install "teaf[redis]"
```

El import de `redis` es **perezoso**, dentro de `connect()`. Construir `RedisCacheProvider` sin el
paquete instalado no falla; falla al conectar, con un mensaje que dice qué instalar. Ese es el
mecanismo que hace la dependencia realmente opcional y no solo opcional sobre el papel.

## 7. Ciclo de vida

Idéntico al del [Database Module](../database/DATABASE.md), a propósito:

| Fase | Qué ocurre |
|---|---|
| `__init__` | Construye configuración y proveedor. **No abre conexiones** — construir es barato y sin efectos. |
| `start()` | `provider.connect()` + `health.refresh()` |
| `ready()` | Registra en el log el backend y la salud conocida |
| `dispose()` | `provider.disconnect()` — simétrico con `start()`, y lo que evita las fugas |

`CacheHealth` sigue el patrón de `DatabaseHealth`: un `check()` **síncrono** que lee una caché y un
`refresh()` **asíncrono** que la actualiza. No es un capricho: `ModuleHealth.check` es síncrono por
diseño del SDK, y un health check no puede abrir una conexión para responder.

## 8. Despliegue

### Local, para desarrollo o para ejecutar las pruebas de integración

```bash
docker run --rm -d -p 6379:6379 --name teaf-redis redis:7-alpine
```

### Azure

[Azure Cache for Redis](https://learn.microsoft.com/azure/azure-cache-for-redis/) es el servicio
gestionado que corresponde al destino de producción declarado en
[ADR-005](../../architecture/adr/ADR-005-cloud-ready.md). Use siempre `rediss://` (TLS) y tome la
cadena de conexión de Key Vault, nunca del repositorio.

## 9. Pruebas

| Suite | Qué cubre | Necesita Redis |
|---|---|---|
| [`tests/unit/test_cache_module.py`](../../../tests/unit/test_cache_module.py) | Contrato, configuración, ciclo de vida, salud, los tres almacenes | No |
| [`tests/integration/test_cache_redis.py`](../../../tests/integration/test_cache_redis.py) | Que los comandos emitidos coincidan con lo que Redis hace de verdad | Sí — **se omite** si no hay servidor |

Las de integración se omiten automáticamente cuando no hay Redis accesible, para que la suite se
pueda ejecutar en cualquier máquina. La URL se toma de `TEAF_TEST_REDIS_URL` o, en su defecto,
`redis://localhost:6379/15` (base 15 por convención, para no tocar la 0 de un Redis de desarrollo).

Que existan **las dos** no es redundancia: el doble en memoria no puede demostrar que los comandos
sean los correctos. De hecho, la suite de integración destapó que `ssl_cert_reqs` se estaba pasando
también sobre URLs `redis://`, donde `SSLConnection` no lo acepta — un fallo que dejaba inutilizable
el backend por defecto y que ninguna prueba sin servidor habría visto.

## 10. Limitación conocida

`RedisQuotaStore.consume` es un **read-modify-write no atómico**: dos réplicas que consuman a la
vez pueden solaparse y permitir un ligero exceso sobre la cuota. Está documentado en el propio
docstring y anotado en el [backlog](../../roadmap/BACKLOG.md).

Se ha preferido dejarlo así, y decirlo, antes que no ofrecer cuotas compartidas: un exceso
ocasional acotado es un problema mucho menor que una cuota multiplicada por el número de réplicas.
Resolverlo del todo exige un script Lua o `INCRBYFLOAT` con una semántica distinta de la del
contrato actual, y eso es un cambio de diseño que este sprint no aborda.

## 11. Referencias

- [ADR-012](../../architecture/adr/ADR-012-redis-optional-infrastructure.md) — la decisión y sus
  alternativas descartadas
- [ADR-009](../../architecture/adr/ADR-009-enterprise-api-protection.md) — los tres almacenes
  preparados que este sprint implementa
- [API-PROTECTION.md](../../api/API-PROTECTION.md) — «De memoria a Redis»
- [Database Module](../database/DATABASE.md) — el patrón que este módulo replica
- [MODULE-CATALOG.md](../../architecture/MODULE-CATALOG.md)
