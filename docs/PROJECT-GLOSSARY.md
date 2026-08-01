# Glosario del proyecto — TEAF

Términos usados de forma consistente en toda la documentación y el código de TEAF, en orden alfabético.

---

**ADR (Architecture Decision Record)** — Registro formal de una decisión arquitectónica: contexto, problema, decisión y consecuencias. Ver [docs/architecture/adr/](architecture/adr/README.md).

**AI Ready** — Principio arquitectónico por el cual el framework provee abstracciones (`backend/ai/`) para integrar Inteligencia Artificial sin acoplar el dominio a un proveedor concreto. Ver [ARCHITECTURE.md](architecture/ARCHITECTURE.md).

**Audit (Auditoría)** — Registro inmutable de acciones sensibles (login, cambios de permisos, bajas) con fines de trazabilidad y cumplimiento. Ver [MODULE-CATALOG.md](architecture/MODULE-CATALOG.md).

**Backlog** — Lista priorizada de Épicas, Features e Historias pendientes del framework. Ver [BACKLOG.md](roadmap/BACKLOG.md).

**Clean Architecture** — Estilo arquitectónico en el que las dependencias siempre apuntan hacia el dominio, nunca hacia afuera (frameworks, infraestructura). Base de la organización en capas de TEAF.

**Cloud Ready** — Principio arquitectónico: ninguna capa asume estado local ni instancia única; toda la aplicación es horizontalmente escalable desde el diseño. Ver [ADR-005](architecture/adr/ADR-005-cloud-ready.md).

**CODEOWNERS** — Archivo de GitHub que define quién debe aprobar cambios en cada parte del repositorio. Ver [.github/CODEOWNERS](../.github/CODEOWNERS).

**Core** — Módulo/carpeta (`backend/core/`) que actúa como kernel transversal del framework: bootstrap, inyección de dependencias, excepciones base.

**Definition of Done (DoD)** — Criterios que determinan cuándo una historia o funcionalidad puede considerarse terminada. Ver [DEFINITION-OF-DONE.md](standards/DEFINITION-OF-DONE.md).

**Dependency Injection (Inyección de dependencias)** — Patrón por el cual las dependencias concretas se proveen desde fuera (`core/`) en vez de instanciarse dentro de la lógica que las usa.

**Épica** — Agrupación de alto nivel de funcionalidades relacionadas dentro del backlog, generalmente alineada a una versión del roadmap. Ver [BACKLOG.md](roadmap/BACKLOG.md).

**Feature** — Capacidad concreta dentro de una épica, compuesta por una o más historias.

**Health Check** — Endpoint (`/health`, `/ready`) que permite a un orquestador (Docker, Azure App Service) verificar que un servicio está disponible.

**Historia (Story/User Story)** — Unidad de trabajo más pequeña y verificable del backlog, con criterios de aceptación explícitos.

**MCP (Model Context Protocol)** — Protocolo estándar para exponer herramientas y contexto a agentes de IA de forma interoperable. Módulo planeado en TEAF (ver [MODULE-CATALOG.md](architecture/MODULE-CATALOG.md)).

**Middleware** — Componente que intercepta toda petición HTTP (o su respuesta) para resolver una preocupación transversal: autenticación, logging, rate limiting. Ver `backend/middleware/`.

**Migración (Migration)** — Cambio versionado y reversible del esquema de base de datos, gestionado con Alembic. Ver [DATABASE-STANDARD.md](standards/DATABASE-STANDARD.md).

**Módulo (Module)** — Unidad funcional del framework con una responsabilidad delimitada (por ejemplo, Security, Scheduler, AI). Ver [MODULE-CATALOG.md](architecture/MODULE-CATALOG.md).

**Observability (Observabilidad)** — Capacidad de entender el comportamiento interno de un sistema a través de trazas, métricas y logs. Ver [LOGGING-STANDARD.md](standards/LOGGING-STANDARD.md).

**OpenTelemetry** — Estándar abierto de instrumentación para trazas, métricas y logs, neutral de proveedor. Tecnología oficial de observabilidad de TEAF. Ver [STACK.md](architecture/STACK.md).

**Quality Gate** — Criterio mínimo no negociable que un cambio debe cumplir antes de fusionarse al framework. Ver [QUALITY-GATES.md](standards/QUALITY-GATES.md).

**Repository (Repositorio de datos)** — Abstracción de acceso a datos que oculta los detalles del motor de persistencia detrás de una interfaz (Repository Pattern). Ver `backend/repository/`.

**RBAC (Role-Based Access Control)** — Modelo de autorización basado en roles y permisos asociados. Ver [SECURITY-STANDARD.md](standards/SECURITY-STANDARD.md).

**Scheduler** — Módulo responsable de tareas programadas (cron) y trabajos diferidos, coordinados de forma segura entre múltiples instancias. Ver `backend/scheduler/`.

**Service Layer (Capa de servicios)** — Capa donde vive la lógica de casos de uso y orquestación de negocio, entre `api/` y `repository/`. Ver `backend/services/`.

**Storage** — Módulo planeado de abstracción de almacenamiento de archivos/blobs. Ver [MODULE-CATALOG.md](architecture/MODULE-CATALOG.md).

**TEAF** — TORUS Enterprise Application Framework: el framework empresarial descrito en este repositorio.

**Telemetry (Telemetría)** — Datos de trazas, métricas y logs recolectados de un sistema en ejecución, base de la observabilidad.

**Webhook** — Mecanismo de notificación de eventos entre sistemas vía HTTP, entrante o saliente. Ver `backend/webhooks/`.
