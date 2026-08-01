# Catálogo de módulos — TEAF

Inventario de todos los módulos previstos del framework, tanto los ya estructurados (con carpeta y `README.md` propios) como los planeados para versiones futuras. Complementa [ARCHITECTURE.md](ARCHITECTURE.md) y [STACK.md](STACK.md). Toda alta o baja de un módulo debe reflejarse aquí (ver [CLAUDE.md](../../CLAUDE.md), sección 14).

**Estado** usa una de estas etiquetas: `Documentado` (tiene carpeta + README, sin código aún), `Planeado — sin carpeta aún` (solo existe en este catálogo y en el roadmap/backlog).

Nivel de reutilización: 🟢 Alto (toda aplicación TORUS lo usará) · 🟡 Medio (la mayoría) · 🔵 Bajo (solo aplicaciones específicas).

---

## Módulos ya estructurados (`backend/`)

| Módulo | Objetivo | Estado | Dependencias | Versión objetivo | Reutilización | Prioridad |
|---|---|---|---|---|---|---|
| [Core](../../backend/core/README.md) | Kernel del framework: bootstrap, DI, excepciones base | Documentado | — | V1 | 🟢 Alto | 🔴 Alta |
| [Configuration](../../backend/config/README.md) | Configuración tipada por entorno, carga de secretos | Documentado | Core | V1 | 🟢 Alto | 🔴 Alta |
| [Database](../../backend/database/README.md) | Motor/sesión SQLAlchemy sobre PostgreSQL | Documentado | Configuration | V1 | 🟢 Alto | 🔴 Alta |
| API | Capa de routers/controladores versionados | Documentado (`backend/api/`) | Core, Security | V1 | 🟢 Alto | 🔴 Alta |
| Services | Casos de uso / Service Layer | Documentado (`backend/services/`) | Repository | V1 | 🟢 Alto | 🔴 Alta |
| Repository | Repository Pattern sobre `models/` | Documentado (`backend/repository/`) | Database | V1 | 🟢 Alto | 🔴 Alta |
| Models | Entidades ORM | Documentado (`backend/models/`) | Database | V1 | 🟢 Alto | 🔴 Alta |
| Schemas | Contratos Pydantic de entrada/salida | Documentado (`backend/schemas/`) | — | V1 | 🟢 Alto | 🔴 Alta |
| [Security](../../backend/security/README.md) | JWT, RBAC, hashing | Documentado | Core | V2 | 🟢 Alto | 🔴 Alta |
| Middleware | Correlation-id, rate limiting, manejo de errores | Documentado (`backend/middleware/`) | Security, Monitoring | V2 | 🟢 Alto | 🔴 Alta |
| [Monitoring](../../backend/monitoring/README.md) (OpenTelemetry) | Trazas, métricas, health checks | Documentado | Core | V2 | 🟢 Alto | 🔴 Alta |
| Shared | Utilidades y tipos genéricos | Documentado (`backend/shared/`) | — | V1 | 🟡 Medio | 🟡 Media |
| [AI](../../backend/ai/README.md) | Abstracciones de cliente LLM, embeddings, vector store | Documentado | Database (pgvector) | V4 | 🟡 Medio | 🟡 Media |
| [Webhooks](../../backend/webhooks/README.md) | Framework de eventos entrantes/salientes | Documentado | Security | V4 | 🟡 Medio | 🟡 Media |
| [Scheduler](../../backend/scheduler/README.md) | Tareas programadas coordinadas multi-instancia | Documentado | Monitoring | V4 | 🟡 Medio | 🟡 Media |

## Módulos planeados (sin carpeta aún)

| Módulo | Objetivo | Estado | Dependencias | Versión objetivo | Reutilización | Prioridad |
|---|---|---|---|---|---|---|
| Notifications | Envío de notificaciones (email, push, chat) desacoplado de proveedor | Planeado — sin carpeta aún | Core, Configuration | V4 | 🟡 Medio | 🟡 Media |
| Storage | Abstracción de almacenamiento de archivos/blobs (local, Azure Blob Storage) | Planeado — sin carpeta aún | Core, Configuration | V4 | 🟡 Medio | 🟡 Media |
| Audit | Registro de auditoría inmutable de acciones sensibles | Planeado — sin carpeta aún | Security, Monitoring | V2 | 🟢 Alto | 🔴 Alta |
| MCP (Model Context Protocol) | Exposición/consumo de herramientas vía MCP para agentes de IA | Planeado — sin carpeta aún | AI | V4 | 🔵 Bajo | 🟢 Baja |
| SAP Connector | Contrato e integración con sistemas SAP | Planeado — sin carpeta aún | Webhooks, Security | V4 | 🔵 Bajo | 🟡 Media |
| Salesforce Connector | Contrato e integración con Salesforce | Planeado — sin carpeta aún | Webhooks, Security | V4 | 🔵 Bajo | 🟡 Media |
| Control-M Connector | Contrato e integración con Control-M | Planeado — sin carpeta aún | Webhooks, Scheduler | V4 | 🔵 Bajo | 🟡 Media |
| GraphQL | Capa de API alternativa a REST para consultas complejas/agregadas | Planeado — sin carpeta aún | API, Services | V5 | 🔵 Bajo | 🟢 Baja |

---

## Cómo actualizar este catálogo

1. Todo módulo nuevo se agrega primero aquí (con su ficha completa) antes de crear la carpeta correspondiente — sigue [`/templates/module-template.md`](../../templates/module-template.md).
2. Al pasar de "Planeado" a "Documentado", enlaza el `README.md` real de la carpeta creada.
3. Cuando exista código ejecutable (a partir de V1), este catálogo introducirá el estado `Implementado` — no se usa todavía porque esta iteración es exclusivamente de estructura y documentación.
