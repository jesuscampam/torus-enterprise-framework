# ADR-012 — Redis como infraestructura opcional para estado compartido entre réplicas

## Estado

**Aceptado** — Sprint 3.0 (v0.10.0-alpha).

Añade `redis-py` a [STACK.md](../STACK.md) como **extra opcional**, según exige CLAUDE.md §4
(«ninguna tecnología fuera de esta lista se introduce sin un ADR aprobado»).

## Contexto

[ADR-009](ADR-009-enterprise-api-protection.md) construyó la plataforma de protección de APIs con
sus almacenes en memoria: `InMemoryRateLimitStore`, `InMemoryQuotaStore`,
`InMemoryIdempotencyStore`. Fue la decisión correcta para Sprint 2.9 —el framework arranca sin
infraestructura desplegada—, y previó el siguiente paso dejando tres clases `Redis*Store` que
cumplían el contrato, documentaban en su docstring qué comando de Redis usaría cada operación, y
lanzaban `NotImplementedError`.

El límite de ese diseño aparece al escalar horizontalmente, y no es sutil: **los almacenes en
memoria son por proceso**. Con 4 réplicas, un límite de 100 peticiones por minuto son 400 en la
práctica, porque cada proceso lleva su propia cuenta y ninguno ve la de los demás. Lo mismo pasa
con las cuotas —se multiplican por el número de réplicas— y con la idempotencia, que es peor: una
petición reintentada que caiga en otra réplica no encuentra el registro y **se ejecuta dos veces**,
que es exactamente lo que la idempotencia existe para impedir.

Es lo que hoy bloquea el escalado horizontal de cualquier aplicación construida sobre TEAF.

## Problema

Hace falta estado compartido entre réplicas. Pero TEAF es un framework base sobre el que se
construirán aplicaciones muy distintas, y muchas correrán en una sola instancia (un POC en Render,
una herramienta interna, la propia suite de pruebas). Añadir una dependencia de infraestructura
obligatoria las castigaría a todas por un problema que solo tienen algunas.

Las dos restricciones, a la vez:

1. Quien despliegue con varias réplicas debe poder compartir estado.
2. Quien no lo necesite no debe pagar **nada**: ni instalar un paquete, ni desplegar un servicio,
   ni ver el camino de la petición encarecido.

## Decisión

### 1. Redis, y por qué no otra cosa

| Candidato | Por qué no |
|---|---|
| **PostgreSQL** (ya en el stack) | Ya está desplegado, lo que es tentador. Pero un contador de rate limiting se escribe en cada petición: convertir eso en escrituras a la base de datos transaccional acopla el camino caliente de *toda* petición a la salud del almacén de negocio, y añade carga de escritura donde más duele. Una caché con expiración nativa es la herramienta para esto. |
| **Memcached** | Sirve para caché, pero carece de expiración por clave con precisión de milisegundos, de tipos de datos útiles para ventanas deslizantes y de persistencia opcional. |
| **Hazelcast / Ignite** | Peso operativo desproporcionado para lo que se necesita. |
| **Redis** | Expiración nativa por clave (`PSETEX`/`PTTL`), operaciones atómicas, cliente asíncrono maduro (`redis-py` con `redis.asyncio`), licencia MIT del cliente, y presencia como servicio gestionado en Azure (Azure Cache for Redis), que es el destino de producción declarado en [ADR-005](ADR-005-cloud-ready.md). |

Se adopta **`redis>=5.0,<7.0`** (cliente `redis-py`, licencia MIT).

### 2. Extra opcional, con import perezoso

`redis` se declara en `[project.optional-dependencies]` como `teaf[redis]`. **El import ocurre
dentro de `connect()`**, no en la cabecera del módulo. No es un detalle de estilo: importar
`redis` al cargar el módulo obligaría a tenerlo instalado para *importar TEAF*, y entonces la
dependencia no sería opcional por mucho que se declare como extra.

Construir `RedisCacheProvider` sin el paquete instalado tampoco falla. Solo falla al conectar —que
es cuando de verdad hace falta— y con un mensaje que dice qué instalar.

### 3. El núcleo nunca conoce Redis: `Core → contrato → provider → Redis`

Se añade [`CacheProvider`](../../../teaf/_internal/contracts/cache.py), espejo deliberado de
`DatabaseProvider`: mismo `connect()`/`disconnect()`/`health_check()`, más `get`/`set(ttl)`/
`delete`/`ttl`/`ping`. Dos implementaciones:

- `InMemoryCacheProvider` — por defecto, sin infraestructura, con purga amortizada para que la
  memoria quede acotada.
- `RedisCacheProvider` — distribuida, tras el extra opcional.

Un consumidor resuelve `CacheProvider` del contenedor y **no puede saber cuál hay detrás**. Ese es
el punto: el acoplamiento a Redis queda confinado a un archivo.

### 4. Un módulo, para que alguien cierre la conexión

`CacheModule` sigue el patrón de `DatabaseModule` sin desviarse: construir no abre conexiones,
`start()` conecta y refresca la salud, `dispose()` cierra. Un proveedor de infraestructura de TEAF
se comporta siempre igual.

Que exista el módulo no es burocracia: **es lo único que garantiza que la conexión se cierre**. Un
proveedor suelto que cada componente construya por su cuenta es una conexión que nadie cierra, y
«ninguna conexión de Redis sobrevive al apagado» es un criterio de bloqueo declarado de este
sprint.

### 5. Los tres almacenes se implementan sobre el contrato — y su constructor cambia

Las tres clases `Redis*Store` pasan de `NotImplementedError` a implementación real. Se apoyan en
`CacheProvider`, **no** en un cliente de Redis propio, para que el ciclo de vida de la conexión
viva en un solo sitio.

ADR-009 se fijó como criterio de éxito que implementarlas no cambiara ninguna firma. **Se cumple
salvo en el constructor**: `get`/`put`/`reset`, `consume`/`peek`/`release` y
`store`/`fetch`/`delete` son idénticas, el registro en DI es el mismo y la configuración del
módulo no cambia; pero los tres pasan de `(url, prefix)` a recibir un `CacheProvider`.

La ruptura es deliberada. `(url, prefix)` daba a cada almacén su propia conexión sin nadie que la
cerrara — precisamente el criterio de bloqueo del punto 4. Mantener la firma habría exigido elegir
entre tres conexiones huérfanas o dos modos de construcción con ciclo de vida ambiguo, y ninguna
de las dos cosas mejora nada real.

**No puede romper a ningún consumidor**: hasta v0.9.2-alpha el constructor lanzaba
`NotImplementedError` incondicionalmente, así que no existe una llamada que antes funcionara y
ahora falle. Aun así `PUBLIC_API_VERSION` sube de `1.0.0` a `2.0.0`, porque
[VERSIONING.md §5](../../public-api/VERSIONING.md) manda subir MAJOR cuando el contrato cambia de
forma incompatible — no cuando además duela. La tabla de migración está en
[MIGRATION-GUIDE.md §6](../../public-api/MIGRATION-GUIDE.md#6-cuando-public_api_version-suba-de-major).

### 6. Una limitación que se documenta en vez de esconderse

`RedisQuotaStore.consume` es un **read-modify-write no atómico**: dos réplicas que consuman a la
vez pueden solaparse y permitir un ligero exceso sobre la cuota. Resolverlo del todo exige un
script Lua o `INCRBYFLOAT` con semántica distinta de la del contrato actual, y eso es un cambio de
diseño que este sprint no aborda.

Se deja implementado y **documentado en el propio docstring**, porque un exceso ocasional acotado
sobre una cuota es un problema mucho menor que no tener cuotas compartidas en absoluto. Queda
anotado en el backlog.

### 7. Coste cero cuando no se configura

Sin configuración no se construye el módulo, no se importa `redis`, y el camino de la petición es
**idéntico** al de v0.9.2-alpha. No es una afirmación de diseño: se verifica con los benchmarks
del sprint.

## Alternativas consideradas

| Alternativa | Por qué se descarta |
|---|---|
| **Dependencia obligatoria** | Castiga a toda aplicación de una sola instancia y rompe «TEAF arranca sin infraestructura desplegada», que es una propiedad que el framework ha mantenido desde Sprint 1. |
| **Reutilizar PostgreSQL como almacén** | Ver tabla del punto 1: acopla el camino caliente de toda petición al almacén transaccional de negocio. |
| **Un `CacheProvider` genérico sin módulo** | Más simple, pero deja el ciclo de vida de la conexión en manos de quien lo construya. Es exactamente la fuga que el punto 4 evita. |
| **Implementar solo el contrato y dejar los tres stores para 3.3** | Habría dejado la funcionalidad sin llegar a nadie: el contrato existe *para* que los stores funcionen, y sin ellos el escalado horizontal sigue bloqueado. |
| **Redis Streams para el EventBus, ya que se añade Redis** | Fuera del alcance de este sprint por decisión explícita (Sprint 3.3). Añadir Redis no es licencia para usarlo en todo. |

## Consecuencias

### Positivas

- **El escalado horizontal deja de estar bloqueado**: rate limiting, cuotas e idempotencia pasan a
  ser correctos con varias réplicas.
- **Coste cero para quien no lo use**, verificado con benchmarks y no solo afirmado.
- **El acoplamiento a Redis cabe en un archivo** (`providers/cache/redis.py`). Sustituirlo por otro
  backend es escribir otro `CacheProvider`.
- **Un `CacheProvider` de propósito general** queda disponible para las aplicaciones, no solo para
  la protección de APIs.

### Negativas

- **Una dependencia más en el stack**, aunque sea opcional: hay que seguir sus CVEs y sus
  versiones, y aparece en `pip-audit`.
- **Un servicio más que operar** para quien lo active: despliegue, credenciales, TLS, copias.
- **Dos caminos de código que probar** (memoria y Redis) en cada almacén. Se mitiga probando el
  contrato contra ambos, pero la superficie de prueba crece.
- **Ruptura de `PUBLIC_API_VERSION`** (punto 5). Inofensiva en la práctica, pero real y visible
  para quien compare versiones.
- **La cuota admite un exceso acotado** con varias réplicas (punto 6), hasta que se implemente de
  forma atómica.
- **Un módulo más en el catálogo**, con su manifiesto, su salud y su documentación que mantener.

### Trade-off aceptado

Se elige **opcionalidad con coste cero** por encima de **simplicidad de implementación**. Una
dependencia obligatoria habría sido bastante más simple de construir y de probar: un solo camino
de código, sin import perezoso, sin extra, sin doble suite. Se ha descartado porque convertiría un
framework que arranca solo en uno que necesita infraestructura desplegada, y esa propiedad vale
más que el código que cuesta conservarla.

## Referencias

- [ADR-009](ADR-009-enterprise-api-protection.md) — plataforma de protección de APIs y los tres
  almacenes preparados
- [ADR-005](ADR-005-cloud-ready.md) — Azure como destino de producción
- [STACK.md](../STACK.md) — justificación de cada tecnología
- [docs/modules/cache/CACHE.md](../../modules/cache/CACHE.md) — uso, configuración y despliegue
- [MIGRATION-GUIDE.md §6](../../public-api/MIGRATION-GUIDE.md#6-cuando-public_api_version-suba-de-major)
- [`tests/integration/test_cache_redis.py`](../../../tests/integration/test_cache_redis.py) —
  verificación contra un Redis real
