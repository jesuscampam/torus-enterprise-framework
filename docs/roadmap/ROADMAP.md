# Roadmap de TEAF

Este roadmap describe la evolución planificada del framework, no de ninguna aplicación construida sobre él. Cada versión se apoya en la anterior y amplía las capacidades disponibles para todas las aplicaciones futuras (TicketGateway, Portal TORUS, Portal NOC, Portal SRE, Inventario TI, Gestor de Incidentes, integraciones SAP/Salesforce/Control-M, IA Empresarial).

Ninguna versión avanza sin aprobación explícita de la iteración anterior.

---

## Versión 0 — Fundación documental (actual)

**Objetivo**: establecer la estructura de carpetas y la documentación base del framework, sin código ejecutable.

- Estructura completa de carpetas de backend, frontend, base de datos, contenedores, scripts, tests y documentación.
- Documentación de arquitectura (`ARCHITECTURE.md`, `STACK.md`), roadmap y primeros ADR.
- Estándares obligatorios: API, base de datos, código, seguridad y logging.
- Gobernanza del repositorio: plantillas de Issues/PR, `CODEOWNERS`, licencia, guía de contribución.

## Versión 1 — Foundation (bootstrap ejecutable)

**Objetivo**: convertir la estructura documental en un esqueleto de código ejecutable, mínimo pero funcional.

- Manifiestos de dependencias del backend (Python) y frontend (Node), con versiones fijadas.
- Aplicación FastAPI mínima: bootstrap en `core/`, sistema de configuración por entorno en `config/`, endpoint de `health check`.
- Conexión a PostgreSQL (`database/`), `Base` declarativa y primera migración Alembic.
- Implementación base del Repository Pattern (interfaz genérica + implementación SQLAlchemy) y de la Service Layer (caso de uso de ejemplo puramente técnico, sin lógica de negocio de producto).
- Contenedores Docker para backend y frontend, y `docker-compose` para desarrollo local (backend + PostgreSQL).
- Pipeline de CI en GitHub Actions: lint, type-check y tests en cada Pull Request.
- Configuración inicial de pruebas unitarias e integración (`tests/unit`, `tests/integration`).

## Versión 2 — Core Services

**Objetivo**: activar las capacidades transversales de seguridad y observabilidad que hoy solo existen como estructura documentada.

- Módulo `security/`: autenticación JWT (access + refresh tokens), autorización RBAC, hashing de credenciales.
- Middlewares (`middleware/`): correlation-id, logging de requests, manejo centralizado de errores (RFC 7807).
- Plataforma de protección y gobernanza de APIs (`api/`): rate limiting (cuatro algoritmos, seis dimensiones), cuotas de consumo, CORS, versionado, validación de borde, compresión, idempotencia y auditoría de API — entregada en el Sprint 2.9 (ver [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md) y [docs/api/API-PROTECTION.md](../api/API-PROTECTION.md)).
- Observabilidad real (`monitoring/`): instrumentación OpenTelemetry (trazas y métricas), exportación compatible con Azure Monitor.
- Framework de manejo de errores y excepciones de dominio homogéneo en toda la capa `api/`.
- Migraciones Alembic como flujo estándar de evolución de esquema, integradas en CI.
- Ampliación de `DATABASE-STANDARD.md` y `SECURITY-STANDARD.md` con ejemplos de implementación real.

## Versión 3 — Frontend Foundation

**Objetivo**: dotar al frontend de una base reutilizable equivalente a la del teaf._internal.

- Shell de aplicación React + TypeScript + Material UI, con theming (`theme/`) parametrizable por aplicación (branding TORUS común, variantes por producto).
- Sistema de autenticación en frontend (flujo JWT, renovación de sesión, rutas protegidas).
- Cliente API tipado (`services/`) generado o alineado con los contratos OpenAPI del backend (coherencia con API First).
- Librería base de componentes (`components/`) para tablas de datos, formularios, navegación y layout empresarial.
- Gestión de estado global (`store/`) y convenciones de `hooks/` reutilizables.
- Configuración por entorno del frontend (`config/`), alineada con `Configuration by Environment`.

## Versión 4 — Integration & AI Ready

**Objetivo**: habilitar las capacidades de integración externa e inteligencia artificial previstas desde el diseño original.

- Abstracciones de IA (`ai/`): interfaces de cliente LLM, gestión de prompts, embeddings y conexión a vector store (`pgvector` sobre PostgreSQL, ver ADR-002), desacopladas de un proveedor concreto.
- Framework de webhooks (`webhooks/`): recepción y emisión de eventos externos con verificación de firma, reintentos y trazabilidad, listo para SAP, Salesforce y Control-M.
- Framework de tareas programadas (`scheduler/`): jobs recurrentes y diferidos, coordinados de forma segura entre múltiples instancias (alineado con Cloud Ready, ADR-005).
- Scaffolding de conectores de integración (contratos e interfaces, sin lógica de negocio de una integración concreta).
- Soporte de multi-tenancy a nivel de framework, si se confirma como requisito transversal de las aplicaciones futuras.

## Versión 5 — Enterprise Hardening & Cloud

**Objetivo**: llevar el framework al nivel de madurez necesario para sostener aplicaciones críticas de producción durante varios años.

- Automatización completa de despliegue a Azure App Service (infraestructura como código, entornos staging/producción).
- Dashboards de observabilidad avanzados (paneles estándar reutilizables por aplicación, alertas).
- Hardening de seguridad: auditoría OWASP Top 10, escaneo de dependencias y de secretos en CI, políticas de rotación de credenciales.
- Pruebas de performance y escalabilidad (carga, estrés) sobre el esqueleto del framework.
- CLI/generador de proyectos (`teaf new app`) para inicializar una nueva aplicación empresarial ya alineada con TEAF en minutos.
- Portal de documentación navegable del framework, generado a partir de `docs/`.

---

## Principio de avance

Cada versión requiere la aprobación explícita de los stakeholders antes de iniciarse. Este roadmap es una guía de intención, no un compromiso de fechas; el alcance de cada versión puede ajustarse a medida que las aplicaciones reales construidas sobre TEAF revelen nuevas necesidades del framework.
