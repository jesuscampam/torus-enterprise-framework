# ADR-009: Enterprise API Protection — Rate Limiting, Quotas y gobernanza de APIs

## Estado

Aceptado

## Contexto

TEAF llega al Sprint 2.9 con tres plataformas empresariales completas —Seguridad ([ADR-007](ADR-007-enterprise-security-stack.md)), Observabilidad ([ADR-008](ADR-008-enterprise-observability-stack.md)) y Base de Datos— y con el Runtime, el `ServiceContainer`, el `EventBus`, el Capability Registry y el Module SDK ya estabilizados desde los Sprints 2.3-2.6. Lo que **no** tiene es ninguna protección del borde HTTP: `teaf/_internal/middleware/` contiene exactamente tres middlewares (correlation-id, logging de peticiones y traducción de excepciones a RFC 7807), y `teaf/_internal/api/` era hasta ahora una carpeta con solo un `README.md` de intención, sin código.

Eso significa que hoy una aplicación TEAF autentica correctamente a quien llama y observa perfectamente lo que ocurre, pero no puede responder a ninguna de estas preguntas: cuántas peticiones por segundo admite de un cliente concreto, cuánto consumo mensual le corresponde a un tenant según su contrato, qué orígenes web pueden invocarla, qué versión de su contrato está sirviendo a cada llamada, qué tamaño máximo de cuerpo acepta, si comprime sus respuestas, qué ocurre cuando un cliente reintenta un `POST` tras un corte de red, y qué registro queda de todo lo anterior para auditoría.

Las aplicaciones previstas sobre TEAF (TicketGateway, Portal TORUS, Portal NOC, integraciones SAP/Salesforce/Control-M) son todas APIs multi-tenant expuestas a consumidores internos y externos con contratos de servicio distintos. Sin esta capa, cada una tendría que resolver los mismos ocho problemas por su cuenta, con ocho criterios distintos — exactamente lo que el framework existe para evitar.

## Problema

¿Cómo construye TEAF una plataforma de protección y gobernanza de APIs completa —limitación de caudal, cuotas contratadas, CORS, versionado, validación de borde, compresión, idempotencia y auditoría— que se integre con Seguridad y Observabilidad sin acoplarse a ellas, que funcione sin infraestructura externa desplegada, que quede preparada para Redis y para gateways externos sin rediseño, y que se consuma exclusivamente a través de la API pública `teaf.api`?

## Decisión

Se crea el subsistema `teaf/_internal/api/`, expuesto públicamente como `teaf.api`, con **ocho subsistemas independientes entre sí** que un único `ApiGateway` compone en una cadena de middlewares, y un `ApiProtectionModule` (Module SDK) que los empaqueta como módulo del Runtime — el mismo patrón de `DatabaseModule`/`SecurityModule`/`ObservabilityModule`.

**Rate limiting.** Se implementan los cuatro algoritmos clásicos (ventana fija, ventana deslizante por registro, cubo de tokens y cubo con fuga) como **funciones puras sobre el estado**: reciben el `RateLimitState` anterior y devuelven el nuevo más la decisión, sin I/O, sin reloj propio y sin conocer el almacén. Esa pureza es lo que permite probarlos exhaustivamente —incluidos los bordes de ventana— sin dormir ni levantar infraestructura, y lo que hace que un mismo `RateLimitStore` sirva a los cuatro sin conocer ninguno. Las reglas se agrupan por seis dimensiones (usuario, API Key, tenant, IP, endpoint, rol) mediante un único enum `ProtectionScope`, **compartido con las cuotas**: ambas necesitan exactamente las mismas dimensiones, y duplicarlo sería la repetición que [CLAUDE.md](../../../CLAUDE.md) §3 prohíbe.

**Quotas.** Subsistema separado del rate limiting, no una variante suya: el rate limiting protege la *disponibilidad* del servicio en ventanas de segundos, las cuotas gobiernan el *consumo contratado* en ventanas de minutos a meses. Cubre las cuatro magnitudes del Sprint (peticiones por minuto/hora/día/mes, ancho de banda, tamaño de payload y peticiones concurrentes), con semánticas deliberadamente distintas: peticiones y ancho de banda acumulan sobre una ventana, el payload es un límite por petición individual que no toca el almacén, y la concurrencia sube al entrar y baja al salir sin ventana temporal.

**Almacenamiento.** Cuatro contratos `async` (`RateLimitStore`, `QuotaStore`, `IdempotencyStore`, `AuditSink`) con implementación **en memoria por defecto** —la plataforma funciona de fábrica sin infraestructura desplegada, mismo criterio que SQLite en `DatabaseModule` y `ConsoleExporter` en `ObservabilityModule`— y una variante **Redis preparada** (`api/providers/redis.py`): las tres clases implementan sus contratos por completo y documentan qué comando de Redis implementa cada operación, sin abrir ninguna conexión, porque `redis-py` no está en [STACK.md](../STACK.md) y añadirlo exigiría su propio ADR. Los contratos son `async` aunque las implementaciones en memoria no hagan I/O: es precisamente eso lo que permite sustituirlas sin cambiar una línea de `RateLimiter`/`QuotaManager`/`IdempotencyManager`.

**CORS.** Se implementa una `CorsPolicy` propia en lugar de usar `CORSMiddleware` de Starlette, por dos razones concretas: TEAF necesita que la política sea un objeto de dominio inspeccionable y componible (declarable en configuración, consultable desde el manifiesto, evaluable en pruebas sin servidor), y necesita comodines de subdominio (`https://*.torus.com`) que Starlette no ofrece.

**Versionado.** Se implementan las tres estrategias (URI, cabecera y tipo de medio) sin imponer ninguna, con versión por defecto, negociación y deprecación vía las cabeceras estándar `Deprecation`/`Sunset`. El middleware deja el resultado en `request.state.api_version` y **no enruta**: elegir qué implementación atiende cada versión es una decisión de la aplicación, y un framework que la impusiera limitaría más de lo que ayuda.

**Compresión.** GZip sobre la librería estándar (siempre disponible) y Brotli sobre un paquete **opcional** (`brotli`/`brotlicffi`): Python no lo trae de serie, y convertirlo en dependencia dura exigiría su propio ADR. Un proveedor no disponible se descarta durante la negociación en vez de romper la petición.

**Idempotencia.** Clave puesta por el cliente (`Idempotency-Key`), huella SHA-256 puesta por el servidor sobre método+ruta+cuerpo, y tres reglas: reutilizar una clave con un cuerpo distinto es un conflicto (HTTP 409) y no una reproducción, solo se guardan respuestas que no sean 5xx, y solo aplica a `POST`/`PATCH` (el resto de verbos ya son idempotentes por definición de HTTP).

**Auditoría.** Un `ApiAuditRecord` por petición con todo lo exigido por el Sprint —incluidos correlation/trace/span-id, que la cruzan con las trazas de ADR-008 sin correlación externa— distribuido a varios destinos a la vez y publicado como evento `audit.recorded`. **Nunca se muestrea**: las trazas sí (`sampling_ratio`) porque son telemetría estadística; la auditoría es un registro de cumplimiento y perder una de cada diez entradas la invalidaría.

**Errores.** Las nueve excepciones del subsistema heredan de `ApplicationException` y declaran su propio `http_status`, un atributo de clase nuevo y opcional en `core/exceptions.py`. Ese punto de extensión evita que `middleware/exception_handler.py` tenga que importar este subsistema —ni ningún otro— para conocer códigos (429/413/415/409) que su jerarquía original no cubría, y mantiene todos los rechazos en el mismo formato RFC 7807 del resto del framework.

### Decisiones de ubicación y superficie, contrarias a la convención vigente

Dos decisiones de este Sprint se apartan de convenciones establecidas en Sprints anteriores. Ambas son deliberadas y quedan registradas aquí precisamente por eso:

1. **`ApiProtectionModule` vive en `teaf/_internal/api/module/`**, junto a su subsistema, y no en `teaf/_internal/modules/` como los otros tres módulos reales. El *patrón* es idéntico (`configuration.py` + `health.py` + `manifest.py` + `module.py`, sobre `ModuleBase`/`ModuleBuilder`); solo cambia dónde viven los cuatro archivos, siguiendo la estructura de `teaf._internal.api` fijada explícitamente por el Sprint.
2. **`ApiProtectionModule` sí se exporta desde `teaf.api`**, a diferencia de `DatabaseModule`/`SecurityModule`/`ObservabilityModule`, que [PUBLIC-API.md](../../public-api/PUBLIC-API.md) §6 mantiene fuera de la superficie pública. El motivo es que la protección de APIs se activa como una unidad —ocho subsistemas con configuración, orden de middlewares y ciclo de vida compartidos—, así que obligar a recomponerla pieza a pieza en cada aplicación sería repetición sin ninguna ganancia de desacoplamiento. Componer manualmente sigue siendo posible: es exactamente el resto de la fachada `teaf.api`.

### Orden de la cadena de middlewares

El orden importa y no es evidente, así que el framework lo fija una vez (`MIDDLEWARE_ORDER`) en lugar de dejarlo a cada aplicación. De más externo a más interno: **CORS** (sus cabeceras deben acompañar también a los errores; un 429 sin ellas se le presenta al desarrollador como un "failed to fetch" genérico), **auditoría** (para ver también lo que rechacen las capas siguientes), **compresión** (actúa sobre la respuesta ya construida), **versionado** antes que **validación** (la versión puede condicionar qué es válido), **rate limiting** antes que **quotas** (no tiene sentido gastar cuota contratada en una petición que va a rechazarse igualmente), e **idempotencia** al final (guarda la respuesta tal y como la produjo el endpoint, sin comprimir y sin cabeceras de capas exteriores).

## Consecuencias

### Positivas

- Las ocho protecciones quedan disponibles para toda aplicación TORUS futura con una sola llamada (`gateway.install(app)`), en lugar de resolverse ocho veces con ocho criterios distintos.
- La plataforma funciona sin infraestructura externa: los proveedores en memoria son el valor por defecto, y migrar a Redis no toca ni `RateLimiter`, ni `QuotaManager`, ni `IdempotencyManager`, ni el registro en DI, ni la configuración del módulo — solo qué implementación de contrato se les pasa.
- Integrar un gateway externo (Azure API Management, Kong, AWS API Gateway) es implementar `ApiProtectionPolicy` (`contracts/api.py`) y pasarlo al `ApiGateway`, sin rediseño.
- Los algoritmos, las políticas y los negociadores son objetos de dominio puros: se prueban, se inspeccionan y se reutilizan fuera de HTTP (desde un worker, un consumidor de cola o un job) mediante `ApiGateway.evaluate()`, sin levantar servidor.
- La integración con Seguridad y Observabilidad es **de consumo, no de acoplamiento**: la protección lee la identidad que `SecurityMiddleware` ya resolvió y el trace-id que `ObservabilityMiddleware` ya estableció, pero ninguno de los tres subsistemas importa a los otros dos.
- Cero dependencias nuevas: todo se construye sobre la librería estándar y sobre lo que TEAF ya declaraba en STACK.md.

### Negativas / Trade-offs

- Los middlewares de compresión, idempotencia y validación de respuesta **materializan el cuerpo completo** de la respuesta, renunciando al streaming real para las peticiones que atraviesan esas capas. Es inevitable —no se puede comprimir ni guardar lo que aún no existe— y por eso la validación de respuesta viene desactivada por defecto.
- Los proveedores en memoria son **por proceso**: en un despliegue multi-instancia cada réplica aplica sus propios límites, así que el límite efectivo es el configurado multiplicado por el número de instancias. Documentado en [RATE-LIMITING.md](../../api/RATE-LIMITING.md); la solución es Redis, que este Sprint deja preparado pero no implementado.
- Brotli no funciona sin instalar un paquete opcional. Es una degradación silenciosa por diseño (`available` a `False` y el negociador lo ignora), lo que evita fallos en producción pero también puede pasar desapercibido si nadie revisa qué codificaciones ofrece realmente el servidor.
- `ApiProtectionModule` expuesto públicamente rompe la regla "ningún módulo real se expone desde `teaf/`", que hasta ahora era absoluta. Queda como excepción documentada, no como derogación: los otros tres módulos siguen sin exponerse.
- La instalación mediante `gateway.install(app)` deja los middlewares de protección **por fuera** de `RequestIdMiddleware`, así que el correlation-id se resuelve leyendo la cabecera entrante en lugar del `ContextVar`. Funciona y está probado, pero es un detalle de orden que cualquier cambio futuro en el arranque de `create_app` debe respetar.
- Ocho middlewares en cadena añaden latencia por petición. Cada uno se salta a sí mismo cuando su subsistema no está configurado, y ninguno se instala si no lo está, pero una aplicación que active los ocho paga ocho saltos de `BaseHTTPMiddleware`.

## Alternativas descartadas

- **Implementar solo rate limiting**, que es lo mínimo que pedía el enunciado inicial. Descartada porque las otras siete protecciones son igual de transversales y de repetibles; entregarlas una a una en Sprints sucesivos habría multiplicado el coste de integración sin reducir el riesgo.
- **Usar `slowapi`, `starlette-limiter` u otra librería de rate limiting.** Ninguna cubre las seis dimensiones de agrupación ni los cuatro algoritmos, todas acoplan el límite a Redis o a un decorador por endpoint, y ninguna se integra con el `EventBus`, el Capability Registry ni la auditoría de TEAF. Adoptarlas habría añadido una dependencia para resolver un tercio del problema.
- **Un único subsistema "throttling" que unificara rate limiting y cuotas.** Comparten dimensiones, pero no propósito, ni orden de magnitud, ni algoritmo, ni almacenamiento: unificarlos habría producido una abstracción con dos modos y ninguna claridad.
- **Delegar toda la protección en un gateway externo** (Azure APIM, Kong). Descartada como *única* vía porque dejaría a las aplicaciones sin protección en desarrollo, en pruebas y en despliegues sin gateway; queda soportada como opción vía `ApiProtectionPolicy`.
