# examples/

Ejemplos mínimos de la API pública de TEAF (`teaf/`, ver [docs/public-api/](../docs/public-api/)). Cada uno importa **exclusivamente** `from teaf import ...` — ninguno conoce `teaf/_internal/` (ver [IMPORT-GUIDE.md](../docs/public-api/IMPORT-GUIDE.md)). Verificado automáticamente por `scripts/check_public_api_boundary.py` y por `tests/unit/test_import_boundary_checker.py`.

## Requisito previo

```bash
pip install -e .
```

## Ejemplos

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`hello-world/`](hello-world/) | Lo mínimo: construir una `Application`, arrancar y apagar su `Runtime`. | `python examples/hello-world/main.py` |
| [`basic-module/`](basic-module/) | Construir un módulo propio con `Module`/`ModuleBuilder` y registrarlo contra un `Runtime`. | `python examples/basic-module/main.py` |
| [`application-bootstrap/`](application-bootstrap/) | Una `Application` completa con un módulo propio ya registrado, más introspección del `Runtime`. | `python examples/application-bootstrap/main.py` |
| [`module-registration/`](module-registration/) | Registrar un módulo con la Module Registration API (`Application(modules=[...])`) — sin `bootstrap()` manual, sin `asyncio.run()`, sin threads. | `python examples/module-registration/main.py` |

Progresión sugerida: léelos en ese orden — cada uno añade una pieza sobre el anterior.

## Plataforma de seguridad (Sprint 2.7, ADR-007)

Cada uno construye su propio `IdentityProviderRegistry`/`PrincipalResolver` y los conecta con `SecurityMiddleware` (`app.asgi.add_middleware(...)`) — el mismo patrón de cableado manual documentado en [`teaf/security.py`](../teaf/security.py) (`SecurityModule` no se expone públicamente, igual que `DatabaseModule`, ver [PUBLIC-API.md](../docs/public-api/PUBLIC-API.md)).

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`jwt-login/`](jwt-login/) | Login con usuario/contraseña (`PasswordHasher`) que emite un JWT (`JWTProvider`), y un endpoint protegido con `@authorize()`. | `python examples/jwt-login/main.py` |
| [`api-key-auth/`](api-key-auth/) | Emitir/usar/rotar/revocar una API Key (`ApiKeyProvider`) y un endpoint protegido por *scope*. | `python examples/api-key-auth/main.py` |
| [`ldap-login/`](ldap-login/) | Bind contra LDAP/Active Directory (`LDAPProvider`) y conversión de grupos a roles. | `python examples/ldap-login/main.py` |
| [`azure-ad-login/`](azure-ad-login/) | Validar tokens de Microsoft Entra ID (`AzureADProvider`): descubrimiento OIDC + JWKS. | `python examples/azure-ad-login/main.py` |
| [`role-based-endpoint/`](role-based-endpoint/) | Proteger un endpoint con `@authorize(role="admin")` (RBAC). | `python examples/role-based-endpoint/main.py` |
| [`permission-based-endpoint/`](permission-based-endpoint/) | Proteger un endpoint con `@authorize(permission=...)`, desacoplado del nombre del rol. | `python examples/permission-based-endpoint/main.py` |
| [`policy-based-endpoint/`](policy-based-endpoint/) | Proteger un endpoint con `@authorize(policy=...)` — una regla arbitraria sobre el `Principal`. | `python examples/policy-based-endpoint/main.py` |
| [`anonymous-endpoint/`](anonymous-endpoint/) | Marcar un endpoint como público a propósito con `@allow_anonymous()`, en contraste con uno protegido. | `python examples/anonymous-endpoint/main.py` |

## Plataforma de observabilidad (Sprint 2.8, ADR-008)

Cada uno construye sus proveedores de OpenTelemetry directamente (`TracerProvider`/`MeterProvider`, dependencias públicas ya declaradas por TEAF) y los envuelve con `teaf.observability` (`OtelTracer`/`OtelMeter`/exportadores) — mismo patrón de cableado manual que la plataforma de seguridad (`ObservabilityModule` no se expone públicamente, igual que `DatabaseModule`/`SecurityModule`, ver [PUBLIC-API.md](../docs/public-api/PUBLIC-API.md)).

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`structured-logging/`](structured-logging/) | Logging JSON estructurado (`get_logger()`) con correlation/trace/span-id, user-id/tenant y contexto libre. | `python examples/structured-logging/main.py` |
| [`distributed-tracing/`](distributed-tracing/) | Spans padre/hijo, atributos, eventos, excepciones y estado (`Tracer`/`Span`) sobre un `TracerProvider` real. | `python examples/distributed-tracing/main.py` |
| [`metrics/`](metrics/) | Los cuatro instrumentos de `Meter`: `Counter`, `UpDownCounter`, `Histogram`, `Gauge`. | `python examples/metrics/main.py` |
| [`health-checks/`](health-checks/) | `/health`/`/ready` agregando el `ModuleHealth` real de varios módulos vía `CompositeHealthChecker`. | `python examples/health-checks/main.py` |
| [`prometheus-metrics/`](prometheus-metrics/) | Métricas expuestas en formato Prometheus (`GET /metrics`, modelo *pull*) con `PrometheusExporter`. | `python examples/prometheus-metrics/main.py` |
| [`opentelemetry-otlp/`](opentelemetry-otlp/) | Exportar trazas y métricas vía OTLP/HTTP a un Collector real — el camino hacia Jaeger/Datadog/Grafana/etc. | `python examples/opentelemetry-otlp/main.py` |

## Plataforma de protección de APIs (Sprint 2.9, ADR-009)

Cada uno construye un `ApiGateway` con los subsistemas que necesita y lo instala con una sola llamada (`gateway.install(app)`), que monta los middlewares en el orden correcto. A diferencia de las dos plataformas anteriores, `ApiProtectionModule` **sí** se expone públicamente (ver [PUBLIC-API.md, sección 8](../docs/public-api/PUBLIC-API.md) y [ADR-009](../docs/architecture/adr/ADR-009-enterprise-api-protection.md)).

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`rate-limiting/`](rate-limiting/) | Los cuatro algoritmos (ventana fija/deslizante, cubo de tokens/con fuga), las dimensiones de agrupación y las cabeceras `X-RateLimit-*`. | `python examples/rate-limiting/main.py` |
| [`quota-management/`](quota-management/) | Las cuatro magnitudes de cuota: peticiones por período, ancho de banda, payload y concurrencia. | `python examples/quota-management/main.py` |
| [`api-versioning/`](api-versioning/) | Versionado por URI, cabecera y tipo de medio, con versión por defecto y deprecación (`Deprecation`/`Sunset`). | `python examples/api-versioning/main.py` |
| [`cors-policy/`](cors-policy/) | Comodines de subdominio, credenciales, comprobación previa y cabeceras CORS en respuestas de error. | `python examples/cors-policy/main.py` |
| [`response-compression/`](response-compression/) | GZip (estándar) y Brotli (paquete opcional), negociación por `Accept-Encoding` y umbral mínimo. | `python examples/response-compression/main.py` |
| [`idempotent-requests/`](idempotent-requests/) | Reintentos que reproducen la respuesta original, y conflicto al reutilizar una clave con otro cuerpo. | `python examples/idempotent-requests/main.py` |
| [`api-audit/`](api-audit/) | Qué se registra de cada petición (aceptada, rechazada, fallida) y cómo se cruza con las trazas. | `python examples/api-audit/main.py` |
