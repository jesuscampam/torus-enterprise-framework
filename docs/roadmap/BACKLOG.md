# Product Backlog — TEAF

Backlog inicial del framework, organizado en **Épicas → Features → Historias**, alineado con las 5 versiones de [ROADMAP.md](ROADMAP.md). Este backlog planifica el propio framework, no aplicaciones de negocio construidas sobre él.

Prioridad: 🔴 Alta · 🟡 Media · 🟢 Baja · ✅ Entregada · ⛔ Bloqueada (la columna de dependencias
explica por qué).

---

## Épica 1 — Foundation (bootstrap ejecutable)

**Versión objetivo**: V1 · **Dependencias**: ninguna (parte de la estructura y documentación ya existentes).

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Manifiestos de dependencias | Definir `backend` (Python) y `frontend` (Node) con versiones fijadas | 🔴 | — |
| Aplicación FastAPI mínima | Bootstrap de `core/`: instancia de la app, registro de routers/middlewares | 🔴 | Manifiestos de dependencias |
| Aplicación FastAPI mínima | Sistema de configuración por entorno en `config/` | 🔴 | Bootstrap de `core/` |
| Aplicación FastAPI mínima | Endpoint de health check (`/health`, `/ready`) | 🔴 | Bootstrap de `core/` |
| Base de datos | Conexión a PostgreSQL y `Base` declarativa en `database/` | 🔴 | Sistema de configuración |
| Base de datos | Primera migración Alembic (esquema vacío/base) | 🔴 | Conexión a PostgreSQL |
| Patrones base | Repository Pattern genérico (interfaz + implementación SQLAlchemy de ejemplo técnico) | 🔴 | Base de datos |
| Patrones base | Service Layer de ejemplo técnico (sin lógica de negocio de producto) | 🔴 | Repository Pattern genérico |
| Contenedores | Dockerfile de backend y de frontend | 🔴 | Manifiestos de dependencias |
| Contenedores | `docker-compose` para desarrollo local (backend + PostgreSQL) | 🔴 | Dockerfiles |
| CI | Pipeline de GitHub Actions: lint, type-check, tests en cada PR | 🔴 | Manifiestos de dependencias |
| Testing | Configuración base de `tests/unit` y `tests/integration` | 🟡 | Aplicación FastAPI mínima |

## Épica 2 — Core Services (seguridad y observabilidad)

**Versión objetivo**: V2 · **Dependencias**: Épica 1 completa.

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Seguridad | Autenticación JWT (access + refresh) en `security/` | 🔴 | Épica 1 |
| Seguridad | Autorización RBAC (roles, permisos) | 🔴 | Autenticación JWT |
| Seguridad | Hashing de credenciales (bcrypt/argon2) | 🔴 | Autenticación JWT |
| Middlewares | Correlation-id, logging de requests | 🔴 | Épica 1 |
| Protección de APIs | Rate limiting: ventana fija/deslizante, cubo de tokens/con fuga, por usuario/API Key/tenant/IP/endpoint/rol (entregado en Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)) | 🔴 | Middlewares |
| Protección de APIs | Cuotas de consumo por período, ancho de banda, payload y concurrencia | 🔴 | Rate limiting |
| Protección de APIs | CORS, versionado de API, validación de borde, compresión, idempotencia y auditoría de API | 🔴 | Middlewares |
| Middlewares | Manejo centralizado de errores (RFC 7807) | 🔴 | Middlewares base |
| Observabilidad | Instrumentación OpenTelemetry (trazas y métricas) en `monitoring/` | 🔴 | Épica 1 |
| Observabilidad | Exportación compatible con Azure Monitor | 🟡 | Instrumentación OpenTelemetry |
| Base de datos | Migraciones Alembic como flujo estándar integrado en CI | 🟡 | Épica 1 (CI) |

## Épica 3 — Frontend Foundation

**Versión objetivo**: V3 · **Dependencias**: Épica 1 (contratos de API disponibles).

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Stack de frontend | Decidir empaquetador, enrutador, estado y pruebas | ✅ | — (ADR-013, Sprint 3.5a) |
| Shell de aplicación | Aplicación React + TypeScript + MUI base | ✅ | Épica 1 (Sprint 3.5a) |
| Autenticación frontend | Flujo de login/renovación de sesión con JWT | ✅ | Épica 2 (Sprint 3.5a) |
| Cliente API | Cliente tipado en `services/` alineado a los contratos OpenAPI | ✅ | Épica 1 (Sprint 3.5a) |
| Estado global | Convenciones de `store/` y `hooks/` reutilizables | ✅ | Shell de aplicación (Sprint 3.5a) |
| Componentes base | Librería base: navegación, layouts, tablas de datos y estados de pantalla | ✅ | Shell de aplicación (Sprint 3.5b) |
| Navegación y rutas | Rutas públicas/privadas, guarda única sobre el layout y ruta inexistente | ✅ | Shell de aplicación (Sprint 3.5b) |
| Theming | Paleta corporativa TORUS, variantes por producto y modo oscuro | 🔴 | Shell de aplicación (Sprint 3.5c) |
| Formularios de escritura | Formularios de alta/edición sobre endpoints de mutación | ⛔ | **Bloqueado**: TEAF no expone endpoints de escritura; corresponde a las aplicaciones, no al framework (CLAUDE.md §10) |
| Paginación de servidor en tablas | Controles de página en `DataTable` | ⛔ | **Bloqueado**: requiere que los endpoints de colección adopten el sobre `CollectionEnvelope` de API-STANDARD.md §4; hoy `/runtime/*` devuelve arrays desnudos |
| Pruebas E2E de frontend | Flujo de login completo contra un backend real | 🟡 | Sprint 3.5a |
| Cliente API generado desde OpenAPI | Generar `types/` desde el esquema en vez de mantenerlos a mano (hoy `types/runtime.ts` se mantiene a mano) | 🟢 | Cliente API |

## Épica 4 — Integration & AI Ready

**Versión objetivo**: V4 · **Dependencias**: Épicas 1 y 2 completas.

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| IA | Interfaz de cliente LLM desacoplada de proveedor en `ai/` | 🔴 | Épica 1 |
| IA | Gestión de embeddings y vector store sobre `pgvector` | 🟡 | Interfaz de cliente LLM |
| IA | Gestión y versionado de prompts | 🟡 | Interfaz de cliente LLM |
| Webhooks | Framework de recepción con verificación de firma en `webhooks/` | 🔴 | Épica 2 (seguridad) |
| Webhooks | Framework de emisión con reintentos | 🟡 | Framework de recepción |
| Scheduler | Framework de tareas recurrentes/diferidas coordinado multi-instancia | 🔴 | Épica 2 (observabilidad) |
| Conectores | Scaffolding de contratos para SAP, Salesforce, Control-M | 🟡 | Framework de webhooks |
| Multi-tenancy | Evaluación y, si aplica, soporte transversal en `repository/` | 🟢 | Épica 1 |

## Épica 5 — Enterprise Hardening & Cloud

**Versión objetivo**: V5 · **Dependencias**: Épicas 1-4 completas.

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Despliegue | Automatización de despliegue a Azure App Service (staging/producción) | 🔴 | Épica 1 (Docker) |
| Observabilidad | Dashboards estándar reutilizables y alertas | 🟡 | Épica 2 |
| Seguridad | Auditoría OWASP Top 10 y escaneo de dependencias/secretos en CI | 🔴 | Épica 2 |
| Performance | Pruebas de carga y estrés sobre el esqueleto del framework | 🟡 | Épica 1 |
| Developer Experience | CLI/generador de proyectos (`teaf new app`) | 🟢 | Épicas 1-3 |
| Documentación | Portal de documentación navegable generado desde `docs/` | 🟢 | — |

### Cerrado en Sprint 3.0

Los cuatro puntos que la línea 2.9 dejó aplazados quedan resueltos. Ninguno de ellos sigue condicionando la declaración de v1.0-beta (ver [PRODUCTION-READINESS.md](../PRODUCTION-READINESS.md)).

| Historia | Desenlace |
|---|---|
| Proveedores Redis de rate limiting, cuotas e idempotencia | ✅ Implementados sobre `CacheProvider` ([ADR-012](../architecture/adr/ADR-012-redis-optional-infrastructure.md)). Desbloquea el escalado horizontal |
| Actualizar FastAPI para cerrar las 7 vulnerabilidades de `starlette` | ✅ `fastapi 0.141.1` / `starlette 1.4.1`. [accepted-vulnerabilities.json](../security/accepted-vulnerabilities.json) queda **vacío**: no hay ninguna vulnerabilidad aceptada |
| Lista de proxies de confianza (`trusted_proxies`) — cierre de H-2 | ✅ `api_trusted_proxies` con verificación de la IP de conexión y lectura de la cadena de derecha a izquierda ([ADR-011](../architecture/adr/ADR-011-trusted-proxy-architecture.md)) |
| Longitud mínima del secreto JWT | ✅ Derivada del algoritmo (RFC 7518 §3.2), validada en `Settings` y en `JWTProvider.__init__` |

#### Cerrado en Sprint 2.9.2

| Historia | Desenlace |
|---|---|
| `SecurityHeadersMiddleware` (H-1) | ✅ Implementado + 31 pruebas ([ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)) |
| `pip-audit` como puerta de calidad | ✅ Puerta `dependencies`; encontró 13 avisos reales y `pyjwt` se actualizó |
| Comentario obsoleto sobre secretos (H-3) | ✅ Corregido |
| Valor por defecto de `trust_forwarded_headers` (H-2) | ⚠️ Mitigado en 2.9.2 (aviso + pruebas anti-spoofing); **cerrado en 3.0** con `api_trusted_proxies` |

### Pendiente tras Sprint 3.0

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Caché | `RedisQuotaStore.consume` es un read-modify-write **no atómico**: dos réplicas concurrentes pueden permitir un ligero exceso sobre la cuota. Resolverlo exige un script Lua o `INCRBYFLOAT` con semántica distinta de la del contrato actual — es un cambio de diseño, no un arreglo. Documentado en su docstring y en [CACHE.md §10](../modules/cache/CACHE.md) | 🟡 | Sprint 3.0 |
| Seguridad | Soportar la cabecera `Forwarded` (RFC 7239) además de `X-Forwarded-For`. Es el estándar formal, pero hoy ningún proxy mayoritario (nginx, Azure Front Door, AWS ALB, Cloudflare) la emite por defecto | 🟢 | [ADR-011](../architecture/adr/ADR-011-trusted-proxy-architecture.md) |
| Aplicación de referencia | Corregir `test_task_module_appears_in_runtime_info` (espera `>= 8` módulos, obtiene 6 desde que los Sprints 2.7/2.8 retiraron los placeholders). Corresponde a su propio repositorio | 🟢 | — |
| Herramientas de desarrollo | `loadtests/harness.py` importa `resource` (POSIX-only) a nivel de módulo — igual que tenía `runtime.py` antes del Windows Compatibility Patch (v0.10.1-alpha). No bloquea `from teaf import Application` porque no está en su cadena de import, así que quedó fuera de ese parche por alcance; correspondería el mismo tratamiento (`process_metrics.py`) si se quiere ejecutar `python -m loadtests` en Windows | 🟢 | [PLATFORM-COMPATIBILITY.md](../PLATFORM-COMPATIBILITY.md) |
| Compatibilidad de plataforma | Validar el Windows Compatibility Patch (v0.10.1-alpha) en una máquina Windows real: `pip install -e .`, `from teaf import Application`, arranque con `uvicorn`, HTTP. Verificado hoy solo en Linux y "compatible por diseño, no verificado" en Windows/macOS — ver [PLATFORM-COMPATIBILITY.md](../PLATFORM-COMPATIBILITY.md) | 🔴 | Acceso a una máquina Windows |
| CI | **Matriz de versiones de Python (3.11 · 3.12 · 3.13 · 3.14) en GitHub Actions.** Sprint 3.0.3 validó las tres primeras y 3.14 ejecutando los intérpretes a mano; 3.12 quedó "compatible por diseño" solo porque no había intérprete disponible. Un fallo como el de 3.14 —que no rompe ninguna prueba, rompe la *instalación*— solo lo detecta una matriz que instale de cero en cada versión. No se implementó en 3.0.3 por alcance: el sprint prohibía crear infraestructura nueva | 🔴 | Épica 1 (CI) |
| Dependencias | **Lockfile para las 5 transitivas nativas que siguen sueltas** (`cryptography`, `cffi`, `argon2-cffi-bindings`, `markupsafe`, `protobuf`). La auditoría del Sprint 3.0.3 encontró 7 transitivas con código nativo sin fijar — la clase de fallo exacta que causó el sprint; se fijó `greenlet` y `pydantic-core` ya está controlada por `pydantic`, pero elegir versión para las otras 5 sin un bloqueo que lo justifique sería actualizar a ciegas. Hacerlo bien exige un lockfile: **decisión de arquitectura, requiere ADR** ([CLAUDE.md](../../CLAUDE.md) §12) | 🟡 | ADR previo |
| Rendimiento | **Ejecutar los benchmarks en una máquina dedicada.** En Sprint 3.0.3 la puerta osciló dentro de la misma sesión: 6 mediciones a +64 %/+80 % y, más tarde, verde otra vez sin tocar la baseline. Confirma el límite ya documentado en [BENCHMARKS.md](../BENCHMARKS.md): en un contenedor compartido la suite detecta regresiones de orden de magnitud, no degradaciones finas | 🟢 | Una máquina dedicada |
| Dependencias | Verificar `asyncpg 0.31.0` (subido en Sprint 3.0.3 por su wheel `cp314`) contra un PostgreSQL real. La suite usa `aiosqlite` y TEAF nunca importa el driver, así que el cambio de pin solo está verificado a nivel de instalación | 🟡 | Un PostgreSQL de pruebas |

### Fuera del alcance de Sprint 3.0 — sprints siguientes

Declarado explícitamente para que no se implemente por adelantado:

| Sprint | Alcance |
|---|---|
| 3.1 | Observabilidad completa (más allá de la base de Sprint 2.8) |
| 3.2 | Gestión empresarial de secretos / Vault |
| 3.3 | EventBus distribuido sobre Redis Streams |
| 3.4 | Resiliencia avanzada: retry, circuit breaker, bulkhead |
| Futuro | Messaging, multi-tenancy, workflows, CLI, UI administrativa |

---

## Cómo mantener este backlog

- Toda historia nueva se añade a la épica correspondiente, con prioridad, dependencias y versión objetivo.
- Si una historia introduce un módulo nuevo, se refleja también en [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md).
- Para historias que requieran más contexto del que cabe en esta tabla, usa [`/templates/issue-template.md`](../../templates/issue-template.md) y enlaza el issue resultante desde la fila correspondiente.
- Este backlog se revisa al cierre de cada versión del [ROADMAP.md](ROADMAP.md), nunca se reordenan las épicas sin actualizar ambos documentos de forma consistente.
