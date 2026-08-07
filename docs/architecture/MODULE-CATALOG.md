# Catálogo de módulos — TEAF

Inventario de todos los módulos previstos del framework, tanto los ya estructurados (con carpeta y `README.md` propios) como los planeados para versiones futuras. Complementa [ARCHITECTURE.md](ARCHITECTURE.md) y [STACK.md](STACK.md). Toda alta o baja de un módulo debe reflejarse aquí (ver [CLAUDE.md](../../CLAUDE.md), sección 14).

**Estado** usa una de estas etiquetas: `Implementado` (tiene código ejecutable y pruebas), `Documentado` (tiene carpeta + README, sin código aún), `Planeado — sin carpeta aún` (solo existe en este catálogo y en el roadmap/backlog).

Nivel de reutilización: 🟢 Alto (toda aplicación TORUS lo usará) · 🟡 Medio (la mayoría) · 🔵 Bajo (solo aplicaciones específicas).

---

## Módulos ya estructurados (`teaf/_internal/`)

| Módulo | Objetivo | Estado | Dependencias | Versión objetivo | Reutilización | Prioridad |
|---|---|---|---|---|---|---|
| [Core](../../teaf/_internal/core/README.md) | Kernel del framework: bootstrap, DI, excepciones base | Documentado | — | V1 | 🟢 Alto | 🔴 Alta |
| [Configuration](../../teaf/_internal/config/README.md) | Configuración tipada por entorno, carga de secretos | Documentado | Core | V1 | 🟢 Alto | 🔴 Alta |
| [Database](../modules/database/DATABASE.md) | Persistencia empresarial: SQLAlchemy 2.x, Unit of Work, Repository Pattern, migraciones Alembic — primer módulo construido sobre el [Module SDK](../sdk/SDK.md) | Implementado (`teaf/_internal/modules/database/` + `teaf/_internal/providers/database/`) | Core | V1 | 🟢 Alto | 🔴 Alta |
| [API Protection](../api/API-PROTECTION.md) | Protección y gobernanza de APIs: rate limiting (4 algoritmos), cuotas, CORS, versionado, validación de borde, compresión, idempotencia y auditoría — cuarto módulo construido sobre el [Module SDK](../sdk/SDK.md) | Implementado (`teaf/_internal/api/`) | Core | V2 | 🟢 Alto | 🔴 Alta |
| Services | Casos de uso / Service Layer | Documentado (`teaf/_internal/services/`) | Repository | V1 | 🟢 Alto | 🔴 Alta |
| Repository | Repository Pattern sobre `models/` | Documentado (`teaf/_internal/repository/`) | Database | V1 | 🟢 Alto | 🔴 Alta |
| Models | Entidades ORM | Documentado (`teaf/_internal/models/`) | Database | V1 | 🟢 Alto | 🔴 Alta |
| Schemas | Contratos Pydantic de entrada/salida | Documentado (`teaf/_internal/schemas/`) | — | V1 | 🟢 Alto | 🔴 Alta |
| [Security](../security/SECURITY-ARCHITECTURE.md) | Autenticación pluggable (`IdentityProvider`: Anonymous/JWT/API Key/LDAP/Azure AD), RBAC, políticas, hashing — segundo módulo construido sobre el [Module SDK](../sdk/SDK.md) | Implementado (`teaf/_internal/modules/security/` + `teaf/_internal/security/`) | Core | V2 | 🟢 Alto | 🔴 Alta |
| Middleware | Correlation-id, rate limiting, manejo de errores | Documentado (`teaf/_internal/middleware/`) | Security, Observability | V2 | 🟢 Alto | 🔴 Alta |
| [Observability](../observability/OBSERVABILITY.md) (OpenTelemetry) | Logging estructurado, tracing distribuido, métricas, health checks compuestos, diagnóstico agregado del Runtime — tercer módulo construido sobre el [Module SDK](../sdk/SDK.md) | Implementado (`teaf/_internal/modules/observability/` + `teaf/_internal/observability/`) | Core | V2 | 🟢 Alto | 🔴 Alta |
| [Monitoring](../../teaf/_internal/monitoring/README.md) | Rutas de sistema (`/health`, `/ready`, `/live`, `/info`) — consume `CompositeHealthChecker` de Observability. | Documentado | Core, Observability | V2 | 🟢 Alto | 🔴 Alta |
| Shared | Utilidades y tipos genéricos | Documentado (`teaf/_internal/shared/`) | — | V1 | 🟡 Medio | 🟡 Media |
| [AI](../../teaf/_internal/ai/README.md) | Abstracciones de cliente LLM, embeddings, vector store | Documentado | Core, Security | V4 | 🟡 Medio | 🟡 Media |
| [Webhooks](../../teaf/_internal/webhooks/README.md) | Framework de eventos entrantes/salientes | Documentado | Security | V4 | 🟡 Medio | 🟡 Media |
| [Scheduler](../../teaf/_internal/scheduler/README.md) | Tareas programadas coordinadas multi-instancia | Documentado | Core | V4 | 🟡 Medio | 🟡 Media |

## Módulos planeados (sin carpeta aún)

| Módulo | Objetivo | Estado | Dependencias | Versión objetivo | Reutilización | Prioridad |
|---|---|---|---|---|---|---|
| Notifications | Envío de notificaciones (email, push, chat) desacoplado de proveedor | Planeado — sin carpeta aún | Core, Configuration | V4 | 🟡 Medio | 🟡 Media |
| Storage | Abstracción de almacenamiento de archivos/blobs (local, Azure Blob Storage) | Planeado — sin carpeta aún | Core, Configuration | V4 | 🟡 Medio | 🟡 Media |
| Audit | Registro de auditoría inmutable de acciones sensibles | Planeado — sin carpeta aún | Security, Monitoring | V2 | 🟢 Alto | 🔴 Alta |
| MCP (Model Context Protocol) | Exposición/consumo de herramientas vía MCP para agentes de IA | Planeado — sin carpeta aún | AI, Core | V4 | 🔵 Bajo | 🟢 Baja |
| SAP Connector | Contrato e integración con sistemas SAP | Planeado — sin carpeta aún | Webhooks, Security | V4 | 🔵 Bajo | 🟡 Media |
| Salesforce Connector | Contrato e integración con Salesforce | Planeado — sin carpeta aún | Webhooks, Security | V4 | 🔵 Bajo | 🟡 Media |
| Control-M Connector | Contrato e integración con Control-M | Planeado — sin carpeta aún | Webhooks, Scheduler | V4 | 🔵 Bajo | 🟡 Media |
| GraphQL | Capa de API alternativa a REST para consultas complejas/agregadas | Planeado — sin carpeta aún | API, Services | V5 | 🔵 Bajo | 🟢 Baja |
| Starter Applications | Aplicaciones de referencia mínimas que validan el framework de extremo a extremo y sirven de punto de partida a nuevos proyectos TORUS | Planeado — sin carpeta aún | Todos los módulos anteriores | V5 | 🟢 Alto | 🟢 Baja |

---

## Nota sobre las dependencias declaradas

La columna "Dependencias" refleja el **grafo estático oficial de dependencias entre módulos**, formalizado en [`docs/architecture/FRAMEWORK-BLUEPRINT.md`](FRAMEWORK-BLUEPRINT.md) (sección 5) y en [`docs/diagrams/dependency-map.mmd`](../diagrams/dependency-map.mmd). No siempre coincide con qué módulos se consultan en tiempo de ejecución:

- **AI** depende únicamente de `Core` y `Security`; nunca accede a `Database` en directo (regla explícita del blueprint). La persistencia de embeddings sobre `pgvector` se realiza exclusivamente a través de `repository/`, igual que cualquier otro dato de dominio.
- **Database** depende de `Core`; en runtime lee su cadena de conexión desde `Configuration`, pero esa relación es de configuración, no una dependencia de módulo.
- **Scheduler** depende de `Core`; se integra con `Monitoring` en runtime para registrar la ejecución de cada job, sin que eso constituya una dependencia dura de módulo.

## Cómo actualizar este catálogo

1. Todo módulo nuevo se agrega primero aquí (con su ficha completa) antes de crear la carpeta correspondiente — sigue [`/templates/module-template.md`](../../templates/module-template.md).
2. Al pasar de "Planeado" a "Documentado", enlaza el `README.md` real de la carpeta creada.
3. Cuando exista código ejecutable, el estado pasa a `Implementado` — usado por primera vez en Sprint 2.6 para el módulo Database, y después para Security (2.7), Observability (2.8) y API Protection (2.9).
