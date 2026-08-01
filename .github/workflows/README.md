# CI/CD — GitHub Actions

Esta carpeta está reservada para los pipelines de integración y entrega continua del framework, basados en **GitHub Actions**, tal como se define en el stack tecnológico oficial (ver [docs/architecture/STACK.md](../../docs/architecture/STACK.md)).

## Estado actual

Aún no hay workflows implementados. Esta iteración del framework se limita a estructura y documentación (ver [docs/roadmap/ROADMAP.md](../../docs/roadmap/ROADMAP.md)).

## Alcance previsto (Versión 1 en adelante)

- **Backend**: lint (`ruff`), formateo (`black`), type-checking (`mypy`), tests unitarios/integración con cobertura mínima, build de imagen Docker.
- **Frontend**: lint (`eslint`), type-checking (`tsc`), tests, build de producción.
- **Base de datos**: verificación de migraciones Alembic (`alembic check` / `upgrade head` contra base efímera).
- **Seguridad**: escaneo de dependencias y de secretos en cada Pull Request.
- **Despliegue**: pipeline de publicación a Render (POC) y a Azure App Service (producción), activado por rama/tag.

Cada workflow deberá cumplir lo establecido en `docs/standards/CODING-STANDARD.md` y `docs/standards/SECURITY-STANDARD.md`.
