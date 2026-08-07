# Product Backlog — TEAF

Backlog inicial del framework, organizado en **Épicas → Features → Historias**, alineado con las 5 versiones de [ROADMAP.md](ROADMAP.md). Este backlog planifica el propio framework, no aplicaciones de negocio construidas sobre él.

Prioridad: 🔴 Alta · 🟡 Media · 🟢 Baja.

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
| Shell de aplicación | Aplicación React + TypeScript + MUI base | 🔴 | Épica 1 |
| Theming | Configuración de tema corporativo en `theme/` | 🔴 | Shell de aplicación |
| Autenticación frontend | Flujo de login/renovación de sesión con JWT | 🔴 | Épica 2 (seguridad backend) |
| Cliente API | Cliente tipado en `services/` alineado a los contratos OpenAPI | 🔴 | Épica 1 |
| Componentes base | Librería base: tablas de datos, formularios, navegación | 🟡 | Shell de aplicación |
| Estado global | Convenciones de `store/` y `hooks/` reutilizables | 🟡 | Shell de aplicación |

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

### Pendiente para Sprint 3.0 (cierre de la línea 2.9)

Estado tras Sprint 2.9.2, que cerró H-1, H-3 y la laguna de auditoría de dependencias. Lo que queda condiciona la declaración de v1.0-beta (ver [PRODUCTION-READINESS.md](../PRODUCTION-READINESS.md)).

| Feature | Historia | Prioridad | Dependencias |
|---|---|---|---|
| Protección de APIs | Implementar los proveedores Redis (rate limiting, cuotas, idempotencia). **Requisito para escalar horizontalmente**: hoy los almacenes son por proceso, así que un límite de 100 req/min con 4 réplicas son 400 en la práctica | 🔴 | ADR nuevo (`redis-py`) |
| Dependencias | Actualizar FastAPI para desbloquear las 7 vulnerabilidades aceptadas de `starlette` (`fastapi 0.115.6` fija `starlette<0.42.0`). Ver [accepted-vulnerabilities.json](../security/accepted-vulnerabilities.json) | 🔴 | Cambio mayor de FastAPI |
| Seguridad | Lista de proxies de confianza (`trusted_proxies`) en sustitución del `trust_forwarded_headers` binario — solución completa de H-2 ([ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)) | 🟡 | Sprint 2.9.2 |
| Seguridad | Longitud mínima del secreto JWT. Hoy no se impone; lo destapó el `InsecureKeyLengthWarning` de pyjwt 2.13.0. Imponerla cambia configuraciones que hoy funcionan | 🟢 | Sprint 2.9.2 |
| Aplicación de referencia | Corregir `test_task_module_appears_in_runtime_info` (espera `>= 8` módulos, obtiene 6 desde que los Sprints 2.7/2.8 retiraron los placeholders). Corresponde a su propio repositorio | 🟢 | — |

#### Cerrado en Sprint 2.9.2

| Historia | Desenlace |
|---|---|
| `SecurityHeadersMiddleware` (H-1) | ✅ Implementado + 31 pruebas ([ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)) |
| `pip-audit` como puerta de calidad | ✅ Puerta `dependencies`; encontró 13 avisos reales y `pyjwt` se actualizó |
| Comentario obsoleto sobre secretos (H-3) | ✅ Corregido |
| Valor por defecto de `trust_forwarded_headers` (H-2) | ⚠️ Mitigado (aviso + pruebas anti-spoofing), no cerrado — ver fila de `trusted_proxies` |

---

## Cómo mantener este backlog

- Toda historia nueva se añade a la épica correspondiente, con prioridad, dependencias y versión objetivo.
- Si una historia introduce un módulo nuevo, se refleja también en [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md).
- Para historias que requieran más contexto del que cabe en esta tabla, usa [`/templates/issue-template.md`](../../templates/issue-template.md) y enlaza el issue resultante desde la fila correspondiente.
- Este backlog se revisa al cierre de cada versión del [ROADMAP.md](ROADMAP.md), nunca se reordenan las épicas sin actualizar ambos documentos de forma consistente.
