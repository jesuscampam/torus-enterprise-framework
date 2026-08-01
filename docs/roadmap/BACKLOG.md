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
| Middlewares | Correlation-id, logging de requests, rate limiting | 🔴 | Épica 1 |
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

---

## Cómo mantener este backlog

- Toda historia nueva se añade a la épica correspondiente, con prioridad, dependencias y versión objetivo.
- Si una historia introduce un módulo nuevo, se refleja también en [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md).
- Para historias que requieran más contexto del que cabe en esta tabla, usa [`/templates/issue-template.md`](../../templates/issue-template.md) y enlaza el issue resultante desde la fila correspondiente.
- Este backlog se revisa al cierre de cada versión del [ROADMAP.md](ROADMAP.md), nunca se reordenan las épicas sin actualizar ambos documentos de forma consistente.
