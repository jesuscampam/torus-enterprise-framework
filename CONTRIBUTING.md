# Guía de contribución — TEAF

Gracias por contribuir al TORUS Enterprise Application Framework. Este documento describe cómo colaborar de forma consistente con el resto del framework.

> Recuerda: este repositorio es el **framework**, no una aplicación de negocio. Toda contribución debe ser genérica, reutilizable y libre de lógica específica de un producto concreto.

## Antes de empezar

1. Lee **[docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)** para entender las capas y principios del framework.
2. Lee los estándares aplicables en **[docs/standards/](docs/standards/)** (API, base de datos, código, seguridad, logging).
3. Si tu cambio implica una decisión arquitectónica relevante (nueva tecnología, cambio de patrón, nueva capa), primero propone un **ADR** (ver [docs/architecture/adr/README.md](docs/architecture/adr/README.md)).

## Flujo de trabajo (branching)

TEAF utiliza **trunk-based development** simplificado:

- `main`: rama estable, siempre desplegable. Protegida — solo se actualiza vía Pull Request.
- `claude/*`, `feature/*`, `fix/*`, `docs/*`: ramas de trabajo, con nombre descriptivo del cambio (`feature/repository-pattern-base`, `fix/jwt-refresh-expiry`, `docs/logging-standard`).

Pasos:

1. Crea una rama a partir de `main`.
2. Realiza tus cambios siguiendo `docs/standards/CODING-STANDARD.md`.
3. Asegúrate de que tu cambio incluye o actualiza documentación y pruebas cuando aplique.
4. Abre un Pull Request usando la plantilla del repositorio.
5. Espera la revisión de al menos un CODEOWNER antes de fusionar.

## Convención de commits

TEAF sigue [Conventional Commits](https://www.conventionalcommits.org/):

```
<tipo>(<alcance opcional>): <descripción breve en imperativo>
```

Tipos permitidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`.

Ejemplos:

```
docs(architecture): agregar ADR-006 sobre estrategia de multi-tenancy
feat(security): implementar rotación de refresh tokens
fix(repository): corregir fuga de sesión en UnitOfWork
```

## Proceso de Pull Request

- El título del PR debe ser claro y seguir la misma convención que los commits.
- Completa todas las secciones de la plantilla de PR (descripción, tipo de cambio, checklist, cómo probar).
- Un PR debe abordar un único propósito. Evita PRs que mezclen refactors no relacionados con la funcionalidad principal.
- Todo PR que introduzca o modifique una capa del framework debe mantener la coherencia con `docs/architecture/ARCHITECTURE.md`; si la contradice, el PR debe actualizar también la documentación.

## Estándares obligatorios

Toda contribución debe cumplir:

- **[API-STANDARD.md](docs/standards/API-STANDARD.md)** — para cualquier cambio en la capa `backend/api/`.
- **[DATABASE-STANDARD.md](docs/standards/DATABASE-STANDARD.md)** — para cambios en `backend/database/`, `backend/models/` o `database/migrations/`.
- **[CODING-STANDARD.md](docs/standards/CODING-STANDARD.md)** — estilo, testing y principios de diseño para todo el código.
- **[SECURITY-STANDARD.md](docs/standards/SECURITY-STANDARD.md)** — obligatorio para cualquier cambio en `backend/security/` o que maneje datos sensibles.
- **[LOGGING-STANDARD.md](docs/standards/LOGGING-STANDARD.md)** — obligatorio para cualquier cambio que emita logs o trazas.

## Registro de decisiones (ADR)

Si tu contribución introduce una decisión arquitectónica significativa (elección de tecnología, patrón estructural, cambio de principio), documenta la decisión como un nuevo ADR siguiendo la plantilla de [docs/architecture/adr/README.md](docs/architecture/adr/README.md), numerado consecutivamente.

## Changelog

Todo cambio visible (nueva capa, nuevo estándar, cambio de arquitectura) debe reflejarse en **[CHANGELOG.md](CHANGELOG.md)** bajo la sección `[Unreleased]`, siguiendo el formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).

## Código de conducta

Se espera un trato profesional, respetuoso y constructivo en toda interacción (revisiones, issues, discusiones). Las críticas deben dirigirse al código y las decisiones, nunca a las personas.
