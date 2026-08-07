# Rate limiting — TEAF

Limitación de caudal de peticiones (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

## 1. Los cuatro algoritmos

Los cuatro están implementados y son intercambiables por configuración (`RateLimitRule.algorithm`). Ninguno es "el correcto": cada uno acierta en un escenario distinto.

| Algoritmo | Cómo funciona | Cuándo elegirlo | Coste de estado |
|---|---|---|---|
| `FIXED_WINDOW` | Un contador por bloque de tiempo alineado al reloj. | Por defecto: el más barato y el más fácil de razonar. | Un entero por clave. |
| `SLIDING_WINDOW` | Registro de las marcas de tiempo de las peticiones aceptadas. | Cuando el límite debe ser exacto en *cualquier* intervalo. | Hasta `limit` marcas por clave. |
| `TOKEN_BUCKET` | Se rellena a ritmo constante; admite ráfagas hasta `burst`. | Cuando se quieren permitir picos cortos sin renunciar al caudal medio. | Dos números por clave. |
| `LEAKY_BUCKET` | La cola se drena a ritmo constante; rechaza al desbordar. | Cuando lo que se protege aguas abajo no tolera ráfagas. | Dos números por clave. |

### Ventana fija

La limitación conocida —y el motivo de que existan las otras tres— es el efecto de borde: un cliente puede emitir `limit` peticiones al final de una ventana y otras `limit` al principio de la siguiente, hasta el **doble** del límite nominal en un instante.

```python
RateLimitRule(name="por-ip", limit=100, window_seconds=60)   # FIXED_WINDOW por defecto
```

### Ventana deslizante

Exacta: nunca permite más de `limit` peticiones en *ningún* intervalo de `window_seconds`, no solo en los bloques alineados. A cambio guarda hasta `limit` marcas de tiempo por clave.

```python
RateLimitRule(name="estricta", limit=100, window_seconds=60,
              algorithm=RateLimitAlgorithm.SLIDING_WINDOW)
```

### Cubo de tokens

`limit`/`window_seconds` fijan el caudal sostenido; `burst` fija cuánta ráfaga se tolera. Un cubo nuevo arranca **lleno**, para no penalizar a un cliente por ser el primero.

```python
# 100/minuto sostenido, pero admite una ráfaga inicial de 300.
RateLimitRule(name="con-rafaga", limit=100, window_seconds=60, burst=300,
              algorithm=RateLimitAlgorithm.TOKEN_BUCKET)
```

### Cubo con fuga

Complementario del anterior: en vez de acumular permisos mientras hay silencio, acumula *trabajo pendiente* y lo drena a caudal fijo. Suaviza el tráfico en lugar de dejarlo pasar a picos — el adecuado cuando se protege una cola de mensajes o un sistema legado.

```python
RateLimitRule(name="suavizada", limit=10, window_seconds=1, burst=50,
              algorithm=RateLimitAlgorithm.LEAKY_BUCKET)
```

### Diferencia que sorprende: quién cuenta los rechazos

En **ventana fija**, una petición rechazada *sí* consume cuota (es el patrón `INCR`-y-compara clásico). En los otros tres, un rechazo **no deja rastro**: un cubo del que no se pudo sacar un token no pierde tokens, y un registro deslizante que anotase los rechazos impediría al cliente recuperarse hasta que pasara la ventana completa. Es el comportamiento estándar de cada uno.

## 2. Las seis dimensiones

`ProtectionScope` decide por qué se agrupa el consumo. Es el mismo enum que usan las [cuotas](QUOTAS.md): ambos necesitan exactamente las mismas dimensiones.

| Dimensión | Clave | Si falta el dato |
|---|---|---|
| `GLOBAL` | `"global"` | — |
| `USER` | `principal_id` del `SecurityContext` | `"anonymous"` |
| `API_KEY` | identificador de la API Key | `"anonymous"` |
| `TENANT` | `tenant_id` | `"default"` |
| `IP` | IP del cliente | `"unknown"` |
| `ENDPOINT` | `"<método> <ruta>"` | — |
| `ROLE` | primer rol en orden alfabético | `"anonymous"` |

El repliegue a `"anonymous"` es deliberado: una regla por usuario debe **seguir limitando** el tráfico sin identificar, no dejarlo pasar sin control.

## 3. Varias reglas a la vez

Todas las reglas aplicables se evalúan y la petición se acepta solo si todas la aceptan. Cuando alguna rechaza, se devuelve la decisión de la **primera** que lo hizo y ninguna posterior llega a consumir cuota.

```python
RateLimiter([
    RateLimitRule(name="por-ip",     limit=100,   window_seconds=60,  scope=ProtectionScope.IP),
    RateLimitRule(name="por-tenant", limit=5_000, window_seconds=60,  scope=ProtectionScope.TENANT),
    RateLimitRule(name="escritura",  limit=10,    window_seconds=1,
                  scope=ProtectionScope.USER, endpoints=("/api/v1/orders*",)),
])
```

`endpoints` admite el comodín final `*` (prefijo); `roles` restringe la regla a quienes tengan alguno de esos roles. Sin ninguno de los dos, la regla aplica a todo.

## 4. Cabeceras de respuesta

| Cabecera | Cuándo | Qué dice |
|---|---|---|
| `X-RateLimit-Limit` | siempre | Límite de la regla más restrictiva. |
| `X-RateLimit-Remaining` | siempre | Cuánto queda antes de chocar. |
| `X-RateLimit-Reset` | siempre | Segundos hasta que se libere cuota. |
| `Retry-After` | solo al rechazar | Segundos a esperar, **redondeados hacia arriba**. |

`X-RateLimit-Remaining` viaja **también en las respuestas correctas**: un cliente bien educado se autorregula antes de chocar, y solo puede hacerlo si esa información llega cuando aún no ha fallado. `Retry-After` se redondea hacia arriba porque decirle a un cliente que espere 0 segundos cuando faltan 0,4 lo haría reintentar de inmediato y volver a chocar.

El rechazo es un `429` con cuerpo RFC 7807, igual que cualquier otro error del framework:

```json
{
  "type": "https://teaf.torus/errors/rate-limit-exceeded",
  "title": "RateLimitExceededException",
  "status": 429,
  "detail": "Se superó el límite de peticiones de la regla 'por-ip'. Reintenta en 18 segundos.",
  "instance": "/api/v1/orders",
  "correlationId": "b1f4..."
}
```

## 5. Detrás de un proxy

`trust_forwarded_headers` decide si se leen `X-Forwarded-For`/`X-Real-IP` para resolver la IP del cliente.

- **`True` (por defecto)**: correcto detrás de un proxy inverso o un balanceador que reescriba esas cabeceras. Sin ello, todas las peticiones compartirían la IP del balanceador y cualquier límite por IP se volvería un límite global.
- **`False`**: obligatorio si la aplicación está expuesta **directamente** a internet. Un cliente puede falsificar `X-Forwarded-For` a voluntad, y confiar en ella dejaría saltarse cualquier límite por IP con solo cambiar un valor.

```python
ApiGateway(rate_limiter=..., trust_forwarded_headers=False)
```

## 6. Fuera de HTTP

`RateLimiter` no depende de Starlette: protege igual un consumidor de cola, un worker o un job.

```python
from teaf.api import ApiRequestContext, RateLimiter, RateLimitRule

limitador = RateLimiter([RateLimitRule(name="cola", limit=50, window_seconds=1)])
contexto = ApiRequestContext(tenant_id="acme")

rechazo = await limitador.acquire(contexto)
if rechazo is not None:
    ...  # aplazar el mensaje
```

`acquire()` devuelve `None` cuando la petición pasa (el caso normal no obliga a interpretar nada) y una `RateLimitDecision` cuando se rechaza. `inspect()` consulta el estado **sin consumir**; `reset()` limpia el de todas las reglas aplicables.

## 7. De memoria a Redis

`RateLimiter` usa `InMemoryRateLimitStore` por defecto: la plataforma funciona sin infraestructura desplegada.

**Limitación**: el estado vive en el proceso. Con N réplicas, el límite efectivo es `limit × N`. Si eso importa, hay dos salidas: configurar `limit / N` por réplica (aproximado, frágil al escalar) o pasar a un almacén distribuido.

`RedisRateLimitStore` (`teaf.api`) deja el segundo camino preparado: implementa el contrato por completo y documenta qué comando de Redis implementa cada operación (un hash con `HSET`/`HGETALL` + `PEXPIRE` sirve a los cuatro algoritmos, porque el estado es opaco para el almacén). No abre conexión: `redis-py` no está en [STACK.md](../architecture/STACK.md) y añadirlo exige su propio ADR. Construirlo lanza `NotImplementedError` explícito.

Cuando ese ADR se apruebe, migrar es sustituir el cuerpo de cada método:

```python
RateLimiter(reglas, store=RedisRateLimitStore(url="redis://cache:6379/0"))
```

Ni `RateLimiter`, ni el registro en DI, ni la configuración del módulo cambian.

## 8. Configuración por entorno

```bash
API_RATE_LIMIT_ENABLED=true
API_RATE_LIMIT_REQUESTS=1000
API_RATE_LIMIT_WINDOW_SECONDS=60
API_RATE_LIMIT_ALGORITHM=token_bucket     # fixed_window | sliding_window | token_bucket | leaky_bucket
API_RATE_LIMIT_SCOPE=tenant               # global | user | api_key | tenant | ip | endpoint | role
API_RATE_LIMIT_BURST=2000
API_TRUST_FORWARDED_HEADERS=true
```

Esa configuración produce **una** regla ("un límite global"). Una aplicación con varias reglas las pasa directamente a `ApiProtectionModule(rate_limit_rules=[...])`, que es más expresivo que intentar codificarlas en cadenas de entorno.

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa y el orden de la cadena.
- [QUOTAS.md](QUOTAS.md) — la diferencia entre limitar caudal y gobernar consumo contratado.
- [`examples/rate-limiting/`](../../examples/rate-limiting/) — ejemplo ejecutable.
