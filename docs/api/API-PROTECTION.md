# Plataforma de protección de APIs — TEAF

Documento de entrada de la plataforma empresarial de protección y gobernanza de APIs de TEAF (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Toda ella se consume exclusivamente desde `teaf.api` — ningún consumidor importa `teaf._internal.api.*` ([IMPORT-GUIDE.md](../public-api/IMPORT-GUIDE.md)).

| Documento | Qué cubre |
|---|---|
| [RATE-LIMITING.md](RATE-LIMITING.md) | Los cuatro algoritmos, las seis dimensiones, cabeceras y despliegue tras proxy. |
| [QUOTAS.md](QUOTAS.md) | Consumo contratado: períodos, ancho de banda, payload y concurrencia. |
| [CORS.md](CORS.md) | Orígenes, comodines de subdominio, credenciales y comprobación previa. |
| [VERSIONING.md](VERSIONING.md) | URI, cabecera y tipo de medio; versión por defecto y deprecación. |
| [IDEMPOTENCY.md](IDEMPOTENCY.md) | Reintentos seguros, huellas y conflictos. |
| [AUDIT.md](AUDIT.md) | Qué se registra de cada petición y cómo se cruza con Observability. |

Validación de peticiones y compresión no tienen documento propio: se cubren en las secciones correspondientes de este mismo archivo, porque su superficie es lo bastante pequeña como para que un documento aparte solo añadiría un salto más de lectura.

---

## 1. Qué resuelve

Antes del Sprint 2.9, una aplicación TEAF autenticaba correctamente a quien llamaba ([SECURITY-ARCHITECTURE.md](../security/SECURITY-ARCHITECTURE.md)) y observaba perfectamente lo que ocurría ([OBSERVABILITY.md](../observability/OBSERVABILITY.md)), pero no podía responder a ninguna de estas preguntas:

- ¿Cuántas peticiones por segundo admito de este cliente?
- ¿Cuánto consumo mensual le corresponde a este tenant según su contrato?
- ¿Qué orígenes web pueden invocar esta API?
- ¿Qué versión de mi contrato estoy sirviendo a esta llamada?
- ¿Qué tamaño de cuerpo acepto, y de qué tipos?
- ¿Comprimo mis respuestas?
- ¿Qué pasa si el cliente reintenta este `POST` tras un corte de red?
- ¿Qué registro queda de todo lo anterior?

Los ocho subsistemas de esta plataforma responden a esas ocho preguntas.

## 2. Arranque rápido

```python
from fastapi import FastAPI
from teaf.api import ApiGateway, RateLimiter, RateLimitRule, CorsPolicy, ApiAudit, InMemoryAuditSink

app = FastAPI()

gateway = ApiGateway(
    rate_limiter=RateLimiter([RateLimitRule(name="por-ip", limit=100, window_seconds=60)]),
    cors=CorsPolicy(allow_origins=("https://app.torus.com",)),
    audit=ApiAudit([InMemoryAuditSink()]),
)
gateway.install(app)
```

`install()` monta los middlewares de los subsistemas configurados, en el orden correcto (§4). Los que no se configuran no se instalan y no cuestan nada.

### Como módulo del Runtime

La alternativa —y lo habitual en una aplicación TEAF completa— es usar `ApiProtectionModule`, que construye los ocho subsistemas a partir de configuración y los registra en el contenedor de dependencias:

```python
from teaf import Application
from teaf.api import ApiProtectionConfiguration, ApiProtectionModule

modulo = ApiProtectionModule(
    ApiProtectionConfiguration(
        rate_limit_requests=100,
        rate_limit_window_seconds=60.0,
        cors_allow_origins=("https://app.torus.com",),
        idempotency_enabled=True,
    )
)
aplicacion = Application(modules=[modulo])
modulo.gateway.install(aplicacion.asgi)   # antes de que arranque el ciclo de vida ASGI
```

> `ApiProtectionModule` es el **único** módulo real que TEAF expone públicamente. Los otros tres (`DatabaseModule`, `SecurityModule`, `ObservabilityModule`) no se exponen. La razón de la excepción está en [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md), "Decisiones de ubicación y superficie".

### Desde configuración por entorno

Todos los campos de `ApiProtectionConfiguration` tienen su equivalente en `Settings` con el prefijo `api_`, y `from_mapping` reconoce ese prefijo:

```python
from teaf import get_configuration
from teaf.api import ApiProtectionConfiguration

configuracion = ApiProtectionConfiguration.from_mapping(get_configuration().model_dump())
```

Las listas viajan como cadenas separadas por comas, porque una variable de entorno no puede ser otra cosa:

```bash
API_RATE_LIMIT_REQUESTS=500
API_CORS_ALLOW_ORIGINS="https://app.torus.com,https://portal.torus.com"
API_QUOTAS_ENABLED=true
API_QUOTA_REQUESTS_PER_DAY=10000
```

## 3. Los ocho subsistemas

| Subsistema | Pieza principal | Qué hace |
|---|---|---|
| Rate limiting | `RateLimiter` | Limita el caudal de peticiones. Cuatro algoritmos, seis dimensiones. |
| Quotas | `QuotaManager` | Gobierna el consumo contratado por período, ancho de banda, payload y concurrencia. |
| CORS | `CorsPolicy` | Decide qué orígenes web pueden invocar la API. |
| Versionado | `ApiVersionNegotiator` | Resuelve, valida y comunica la versión servida. |
| Validación | `RequestValidator` | Rechaza en el borde por tamaño, tipo, cabeceras o agente. |
| Compresión | `CompressionNegotiator` | Comprime respuestas en GZip o Brotli. |
| Idempotencia | `IdempotencyManager` | Reproduce la respuesta original de un reintento. |
| Auditoría | `ApiAudit` | Registra cada petición servida. |

Todos son utilizables **por separado**, fuera de HTTP. Un `RateLimiter` puede proteger un consumidor de cola; una `CorsPolicy` puede evaluarse en una prueba; un `ApiAudit` puede alimentarse desde un job.

## 4. Orden de la cadena

`ApiGateway` fija el orden una vez (`MIDDLEWARE_ORDER`) porque importa y no es evidente. De **más externo a más interno**:

```
CORS → auditoría → compresión → versionado → validación → rate limiting → quotas → idempotencia → endpoint
```

- **CORS primero**: sus cabeceras deben acompañar también a los errores. Un `429` sin ellas se le presenta al desarrollador como un "failed to fetch" genérico en lugar del motivo real.
- **Auditoría después**: así ve también lo que rechacen las capas siguientes. Una auditoría que solo viera el tráfico aceptado sería inútil para lo que más importa auditar.
- **Compresión** actúa sobre la respuesta ya construida.
- **Versionado antes que validación**: la versión puede condicionar qué se considera válido.
- **Rate limiting antes que quotas**: el límite de caudal es más barato de evaluar, y no tiene sentido gastar cuota contratada en una petición que va a rechazarse igualmente.
- **Idempotencia al final**: guarda la respuesta tal y como la produjo el endpoint, sin comprimir y sin cabeceras de capas exteriores.

Starlette ejecuta los middlewares en orden inverso al de registro, así que `install()` los añade recorriendo esa cadena al revés. **`install()` debe llamarse antes de que arranque el ciclo de vida ASGI**: Starlette congela su pila de middlewares en el primer arranque.

## 5. Validación de peticiones

Se evalúa **antes** de que la petición llegue al endpoint, y sobre metadatos, no sobre el payload (de eso ya se encarga Pydantic). La distinción importa por seguridad: rechazar un cuerpo de 500 MB por su `Content-Length` cuesta microsegundos, mientras que dejar que Pydantic intente parsearlo cuesta memoria y CPU que decide el cliente.

```python
from teaf.api import RequestValidator, RequestValidationPolicy

validador = RequestValidator(
    RequestValidationPolicy(
        max_request_bytes=1024 * 1024,
        allowed_content_types=("application/json",),
        required_headers=("X-Tenant",),
        blocked_user_agents=("BadBot",),
        max_url_length=4_000,
    )
)
```

| Regla | Código HTTP |
|---|---|
| Cuerpo mayor que `max_request_bytes` | `413 Request Too Large` |
| `Content-Type` fuera de `allowed_content_types` | `415 Unsupported Media Type` |
| Falta una cabecera de `required_headers` | `400 Bad Request` |
| `User-Agent` bloqueado o fuera de la lista blanca | `400 Bad Request` |
| URL más larga que `max_url_length` | `400 Bad Request` |
| Respuesta mayor que `max_response_bytes` | `500 Internal Server Error` |

La respuesta desbordada es un `500` y no un `4xx` a propósito: la petición era válida y fue el servidor quien produjo algo fuera del contrato declarado. Esa comprobación viene **desactivada** por defecto (`validate_responses=False`) porque obliga a materializar el cuerpo de toda respuesta.

Los métodos sin cuerpo (`GET`/`HEAD`/`DELETE`/`OPTIONS`/`TRACE`) y los cuerpos vacíos nunca necesitan declarar `Content-Type`.

## 6. Compresión

```python
from teaf.api import CompressionNegotiator, CompressionPolicy, GzipCompressionProvider, BrotliCompressionProvider

negociador = CompressionNegotiator(
    [BrotliCompressionProvider(quality=4), GzipCompressionProvider(level=6)],
    policy=CompressionPolicy(minimum_size_bytes=500),
)
```

- **GZip siempre está disponible** (librería estándar). **Brotli requiere `pip install brotli`** (o `brotlicffi`): no es dependencia dura del framework porque añadirla exigiría su propio ADR ([STACK.md](../architecture/STACK.md), [CLAUDE.md](../../CLAUDE.md) §4). Si falta, `available` es `False` y el negociador simplemente no lo elige.
- Manda la preferencia del **cliente** (`Accept-Encoding` con sus factores `q`), no la del servidor — es lo que exige HTTP.
- Por debajo de `minimum_size_bytes` no se comprime: el ahorro no compensa la CPU ni las ~20 bytes de cabecera del propio formato.
- Solo se comprimen tipos que se benefician (texto, JSON, XML, SVG). Un JPEG o un ZIP ya vienen comprimidos.
- Si el resultado comprimido no es más pequeño, se devuelve el original.
- `Vary: Accept-Encoding` va siempre, para que ninguna caché sirva la respuesta comprimida a un cliente que no la admite.

## 7. Integración con Security y Observability

La integración es **de consumo, no de acoplamiento**: ninguno de los tres subsistemas importa a los otros dos.

- **Con Security (Sprint 2.7)**: la protección lee el `SecurityContext` que `SecurityMiddleware` ya resolvió, para agrupar límites y cuotas por usuario, API Key, tenant o rol. La plataforma nunca autentica por su cuenta. Si la identidad aún no está resuelta, el contexto es anónimo y se limita por IP — que es el comportamiento correcto para tráfico sin identificar.
- **Con Observability (Sprint 2.8)**: cada `ApiAuditRecord` lleva `correlationId`/`traceId`/`spanId`, así que desde una entrada de auditoría se salta a la traza completa. Pasándole el `Meter` de `ObservabilityModule`, `ApiAudit` emite además un contador de peticiones auditadas y un histograma de latencias.
- **Con el Runtime (Sprint 2.3-2.4)**: `ApiProtectionModule` registra sus servicios en el `ServiceContainer`, declara nueve capacidades en el Capability Registry, publica ocho eventos en el `EventBus` y aporta un health check a `/health`.

## 8. Eventos publicados

| Evento | Cuándo |
|---|---|
| `request.accepted` | Una petición se sirvió correctamente. |
| `request.rejected` | Cualquier middleware la rechazó (incluye el motivo). |
| `rate.limit.exceeded` | Se superó una regla de limitación. |
| `quota.exceeded` | Se agotó una cuota. |
| `idempotency.detected` | Se reprodujo la respuesta de un reintento. |
| `request.compressed` | Se comprimió una respuesta (con tamaños antes/después). |
| `audit.recorded` | Se registró una entrada de auditoría. |
| `version.negotiated` | Se resolvió la versión de API de una petición. |

## 9. Servicios registrados en el contenedor

`ApiProtectionModule` registra automáticamente, cuando su subsistema está configurado:

`ApiGateway` · `RateLimiter` · `QuotaManager` · `ApiAudit` · `RequestValidator` · `IdempotencyManager` · `CompressionProvider`

```python
from teaf.api import RateLimiter
limitador = aplicacion.runtime.resolve_service(RateLimiter)
```

Un servicio cuyo subsistema no está configurado **no se registra**: resolverlo falla de forma clara en lugar de devolver algo inservible.

## 10. De memoria a Redis

Los cuatro contratos de almacenamiento (`RateLimitStore`, `QuotaStore`, `IdempotencyStore`, `AuditSink`) tienen implementación en memoria por defecto — la plataforma funciona de fábrica sin infraestructura desplegada, mismo criterio que SQLite en `DatabaseModule`.

**Limitación conocida y documentada**: el estado vive en el proceso. Con varias instancias, cada una aplica sus propios límites, así que el límite efectivo es el configurado × número de réplicas.

`teaf/_internal/api/providers/redis.py` deja los tres proveedores distribuidos **preparados**: implementan sus contratos por completo y documentan qué comando de Redis implementa cada operación, pero no abren ninguna conexión — `redis-py` no está en [STACK.md](../architecture/STACK.md) y añadirlo exige su propio ADR. Construir cualquiera de ellos lanza `NotImplementedError` de forma explícita; nunca falla en silencio.

Migrar, cuando ese ADR se apruebe, es sustituir el cuerpo de cada método. Ni la firma, ni el registro en DI, ni la configuración del módulo cambian.

## 11. Gateways externos

`ApiProtectionPolicy` (`teaf.api`) es el contrato preparado para delegar la protección en Azure API Management, Kong o AWS API Gateway: implementarlo y pasarlo al `ApiGateway`, sin rediseñar la plataforma. No se descarta el uso de un gateway externo — se descarta como *única* vía, porque dejaría a las aplicaciones sin protección en desarrollo, en pruebas y en despliegues sin gateway.

## 12. Coste de los middlewares que leen el cuerpo

Compresión, idempotencia y validación de respuesta **materializan el cuerpo completo** de la respuesta, renunciando al streaming real para las peticiones que atraviesan esas capas. Es inevitable: no se puede comprimir ni guardar lo que aún no existe. Consecuencias prácticas:

- La validación de respuesta viene desactivada por defecto.
- Una API que sirva descargas grandes o *server-sent events* no debería montar compresión sobre esas rutas.
- Los ocho middlewares se saltan a sí mismos cuando su subsistema no está configurado, y ninguno se instala si no lo está.

## 13. Ejemplos ejecutables

| Ejemplo | Qué demuestra |
|---|---|
| [`rate-limiting/`](../../examples/rate-limiting/) | Los cuatro algoritmos y las dimensiones de agrupación. |
| [`quota-management/`](../../examples/quota-management/) | Las cuatro magnitudes de cuota. |
| [`api-versioning/`](../../examples/api-versioning/) | Las tres estrategias, la versión por defecto y la deprecación. |
| [`cors-policy/`](../../examples/cors-policy/) | Comodines de subdominio, credenciales y preflight. |
| [`response-compression/`](../../examples/response-compression/) | GZip, Brotli opcional y negociación. |
| [`idempotent-requests/`](../../examples/idempotent-requests/) | Reintentos, reproducción y conflictos. |
| [`api-audit/`](../../examples/api-audit/) | Qué se registra y cómo se cruza con las trazas. |
