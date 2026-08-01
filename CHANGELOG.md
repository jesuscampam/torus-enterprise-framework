# Changelog

Todos los cambios relevantes de este proyecto se documentan en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto sigue [Versionado Semántico](https://semver.org/lang/es/).

## [Unreleased]

### Added

- Estructura inicial del monorepo del framework: `backend/`, `frontend/`, `database/`, `docker/`, `scripts/`, `tests/`, `docs/`, `.github/`.
- Documentación base de arquitectura: `docs/architecture/ARCHITECTURE.md` y `docs/architecture/STACK.md`.
- Roadmap del framework con 5 versiones planificadas: `docs/roadmap/ROADMAP.md`.
- Primeros 5 Architecture Decision Records (ADR-001 a ADR-005) sobre FastAPI, PostgreSQL, Docker, API First y Cloud Ready.
- Estándares obligatorios del framework: API, base de datos, código, seguridad y logging (`docs/standards/`).
- Gobernanza de GitHub: `CODEOWNERS`, plantillas de Issues y Pull Request, `CONTRIBUTING.md`.
- Licencia MIT del proyecto.

### Notes

- Esta iteración es exclusivamente de **estructura y documentación**. No incluye código ejecutable, endpoints, pantallas, manifiestos de dependencias ni pipelines de CI/CD reales. Estos se incorporarán en la Versión 1 (ver `docs/roadmap/ROADMAP.md`).

[Unreleased]: https://github.com/jesuscampam/torus-enterprise-framework/compare/main...HEAD
