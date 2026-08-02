# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

Sin cambios todavía sobre [0.2.0-alpha](#020-alpha---2026-08-02).

## [0.2.0-alpha] - 2026-08-02

### Added

- Estructura inicial del monorepo del framework: `backend/`, `frontend/`, `database/`, `docker/`, `scripts/`, `tests/`, `docs/`, `.github/`.
- Documentación base de arquitectura: `docs/architecture/ARCHITECTURE.md` y `docs/architecture/STACK.md`.
- Roadmap del framework con 5 versiones planificadas: `docs/roadmap/ROADMAP.md`.
- Primeros 5 Architecture Decision Records (ADR-001 a ADR-005) sobre FastAPI, PostgreSQL, Docker, API First y Cloud Ready.
- Estándares obligatorios del framework: API, base de datos, código, seguridad y logging (`docs/standards/`).
- Gobernanza de GitHub: `CODEOWNERS`, plantillas de Issues y Pull Request, `CONTRIBUTING.md`.
- Licencia MIT del proyecto.
- `CLAUDE.md`, `/templates/` (9 plantillas reutilizables), estándar de Git (`GIT-STANDARD.md`), backlog inicial (`BACKLOG.md`), catálogo de módulos (`MODULE-CATALOG.md`), quality gates, definition of done y glosario del proyecto.
- Framework Blueprint oficial (`docs/architecture/FRAMEWORK-BLUEPRINT.md`) con 12 diagramas Mermaid (arquitectura por capas, mapa de dependencias, flujos de inicialización/petición/excepción, arquitectura física de despliegue, arquitectura de seguridad, proveedores de IA y MCP) y documentos complementarios `NFR.md`, `DECISION-TREE.md`, `EXTENSIBILITY.md`.
- **Bootstrap ejecutable del framework** (Sprint 2.1): Application Factory (`backend/core/application.py`), configuración por entorno (Development/Testing/Staging/Production), logging estructurado (consola/JSON/archivo con rotación), jerarquía de excepciones (`ApplicationException` y 6 subtipos), middlewares de correlation-id y logging de peticiones, manejo centralizado de errores en formato RFC 7807, rutas de sistema (`/`, `/health`, `/live`, `/ready`), utilidades genéricas en `shared/`, y suite de pruebas base (`tests/unit/`, `tests/integration/`). Documentado en `docs/core/CORE.md`.
- Manifiestos de dependencias del backend (`requirements.txt`, `requirements-dev.txt`) y configuración de herramientas (`pyproject.toml`: ruff, black, mypy, pytest).
- **Infrastructure Foundation** (Sprint 2.2): paquete `backend/contracts/` con 9 interfaces puras (Repository, UnitOfWork, DatabaseProvider, Authentication/AuthorizationProvider, TelemetryProvider, StorageProvider, AIProvider, SchedulerProvider, NotificationProvider); paquete `backend/providers/` con clases base y factories abstractas para database (`DatabaseFactory`, `DatabaseSession`, `ConnectionManager`, `RepositoryBase`), security (`SecurityContext`, `AuthenticationManager`, `AuthorizationManager`, RBAC, `SecurityFactory`), telemetry (`TracerProvider`, `MetricsProvider`, `LoggerProvider`, `TelemetryContext`), storage y ai; `ModuleRegistry` (`backend/core/registry.py`) registrado por instancia de aplicación (no como singleton de proceso); expansión de la inyección de dependencias (`backend/providers/dependencies.py`); nueva ruta `/info` con versión y estado de los módulos registrados. Documentado en `docs/infrastructure/INFRASTRUCTURE.md`. 32 pruebas nuevas (contracts, registry, factories, DI) — sin integraciones reales.

### Changed

- `README.md`: la sección "Cómo iniciar el proyecto" ahora documenta pasos reales de arranque (`uvicorn backend.main:app --reload`), en vez de la nota de "sin código ejecutable" de la iteración de fundación.
- Versión del framework (`FRAMEWORK_VERSION` en `backend/core/application.py`, expuesta en `/health` y `/info`): `0.1.0` → `0.2.0-alpha`.

### Notes

- El backend ya es ejecutable end-to-end (`uvicorn backend.main:app --reload` responde en `/`, `/health`, `/live`, `/ready`, `/info`). Sigue sin haber base de datos, autenticación, frontend ejecutable, Docker ni CI/CD reales — llegan en Sprints posteriores (ver `docs/roadmap/ROADMAP.md`, Versión 1 en adelante).
- Sprint 2.2 es exclusivamente infraestructura abstracta: contratos y clases base, sin ninguna implementación ni conexión real (sin PostgreSQL, SQLAlchemy funcional, JWT/OAuth, IA, MCP, storage ni scheduler reales).

[Unreleased]: https://github.com/jesuscampam/torus-enterprise-framework/compare/v0.2.0-alpha...HEAD
[0.2.0-alpha]: https://github.com/jesuscampam/torus-enterprise-framework/compare/main...v0.2.0-alpha
