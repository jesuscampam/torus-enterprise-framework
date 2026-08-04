# CLAUDE.md — Memoria del proyecto TEAF

Este documento es la memoria permanente de **TEAF (TORUS Enterprise Application Framework)** para Claude Code y cualquier agente de IA que trabaje en este repositorio. Se carga automáticamente al iniciar una sesión en la raíz del proyecto. Toda instrucción aquí prevalece sobre supuestos genéricos de "buenas prácticas" cuando entren en conflicto.

## 1. Visión del framework

TEAF **no es una aplicación de negocio**: es el framework empresarial base sobre el que se construyen todas las aplicaciones futuras de TORUS (TicketGateway, Portal TORUS, Portal NOC, Portal SRE, Inventario TI, Gestor de Incidentes, integraciones SAP/Salesforce/Control-M, IA Empresarial, etc.). Ninguna lógica de negocio de una aplicación concreta pertenece a este repositorio. Visión completa: [README.md](README.md) · Arquitectura completa: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

## 2. Objetivos

Reutilización entre aplicaciones, consistencia arquitectónica, velocidad de arranque de nuevos proyectos, calidad impuesta desde el primer commit (Clean Architecture, SOLID), preparación nativa para nube (Azure) e IA, observabilidad de extremo a extremo, y una base mantenible durante varios años tanto por humanos como por agentes de IA. Detalle en [README.md](README.md#objetivos).

## 3. Filosofía de desarrollo

- **Clean Architecture** con dependencias que siempre apuntan hacia adentro (`api → services → repository → database`).
- **SOLID, DRY, KISS**: no se introduce abstracción, capa o patrón sin una necesidad concreta y actual. No se diseña para requisitos hipotéticos.
- **API First**: el contrato se diseña antes que la implementación.
- **AI Ready** y **Cloud Ready** desde el diseño, no como añadido posterior.
- **Sin sobre-ingeniería**: tres líneas similares son preferibles a una abstracción prematura. Ver [ADR-004](docs/architecture/adr/ADR-004-api-first.md) y [ADR-005](docs/architecture/adr/ADR-005-cloud-ready.md) como ejemplo del nivel de rigor esperado en cada decisión.
- **Construido para años, no para sprints**: cada decisión debe poder sostenerse y explicarse dentro de 3-5 años; de ahí la obligatoriedad de los ADR.

## 4. Tecnologías oficiales

FastAPI · React + TypeScript · PostgreSQL · SQLAlchemy · Alembic · Docker · GitHub Actions · Render (POC) · Azure App Service (producción) · OpenTelemetry · JWT · Material UI.

Justificación completa de cada elección: [docs/architecture/STACK.md](docs/architecture/STACK.md). **Ninguna tecnología fuera de esta lista se introduce sin un ADR aprobado** (ver sección 12).

## 5. Arquitectura oficial

```
Cliente → middleware/ → api/ → services/ → repository/ → database/ + models/
          Transversales: core/ · config/ · security/ · monitoring/ · shared/ · ai/ · webhooks/ · scheduler/
```

Regla no negociable: **una capa nunca importa una capa más externa que ella**. `repository/` no conoce `api/`; `services/` no conoce detalles HTTP; `api/` no ejecuta SQL. Detalle completo, tabla de responsabilidades por capa y flujo de una petición: [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md).

## 6. Convenciones

- Toda la documentación se redacta en **español**.
- Nombres de carpeta en `snake_case` (Python) o `camelCase`/`PascalCase` según corresponda en frontend (ver sección 7).
- Cada carpeta de código lleva un `README.md` que documenta su responsabilidad — nunca se deja una carpeta sin documentar.
- Toda decisión estructural nueva pasa primero por `/templates/module-template.md` y, si aplica, por un ADR.
- Los documentos de gobierno (`docs/standards/`, `docs/architecture/`, `docs/roadmap/`) son la fuente de verdad; este archivo resume y enlaza, no duplica su contenido en extenso.

## 7. Reglas de codificación

Resumen operativo — el detalle completo vive en cada estándar, léelo antes de tocar la capa correspondiente:

| Estándar | Cuándo consultarlo |
|---|---|
| [CODING-STANDARD.md](docs/standards/CODING-STANDARD.md) | Siempre: estilo, principios SOLID/DRY/KISS, testing, checklist de revisión. |
| [API-STANDARD.md](docs/standards/API-STANDARD.md) | Antes de tocar `teaf/_internal/api/` o `teaf/_internal/schemas/`. |
| [DATABASE-STANDARD.md](docs/standards/DATABASE-STANDARD.md) | Antes de tocar `teaf/_internal/database/`, `teaf/_internal/models/`, `teaf/_internal/repository/` o `database/migrations/`. |
| [SECURITY-STANDARD.md](docs/standards/SECURITY-STANDARD.md) | Antes de tocar `teaf/_internal/security/` o cualquier dato sensible. |
| [LOGGING-STANDARD.md](docs/standards/LOGGING-STANDARD.md) | Antes de emitir logs, métricas o trazas. |
| [GIT-STANDARD.md](docs/standards/GIT-STANDARD.md) | Siempre: ramas, commits, versionado. |
| [QUALITY-GATES.md](docs/standards/QUALITY-GATES.md) | Antes de abrir cualquier Pull Request. |
| [DEFINITION-OF-DONE.md](docs/standards/DEFINITION-OF-DONE.md) | Antes de marcar una historia/feature como terminada. |

## 8. Reglas específicas para IA (Claude Code)

1. Antes de escribir o modificar código, lee `docs/architecture/ARCHITECTURE.md` y el estándar de la capa afectada (tabla de la sección 7).
2. No introduzcas una tecnología, librería o patrón fuera de [STACK.md](docs/architecture/STACK.md) sin proponer antes un ADR (sección 12) y obtener aprobación explícita del usuario.
3. No saltes capas: si necesitas datos en `api/`, pasa por `services/` y `repository/`, nunca accedas a `database/`/`models/` directamente.
4. Antes de crear un patrón nuevo (endpoint, repositorio, servicio, migración, componente), revisa si existe una plantilla aplicable en [`/templates/`](templates/README.md) y extiéndela en vez de inventar uno desde cero.
5. Toda decisión con impacto en más de un módulo o aplicación futura se documenta como ADR — no se implementa "silenciosamente".
6. Actualiza `CHANGELOG.md` en `[Unreleased]` en cualquier cambio visible; actualiza `docs/roadmap/BACKLOG.md` y `docs/architecture/MODULE-CATALOG.md` cuando el cambio afecte su contenido.
7. Cuando la petición del usuario sea ambigua respecto al alcance de una iteración (por ejemplo, "solo estructura" vs. "código funcional"), pregunta antes de asumir el alcance mayor.
8. Nunca autoapruebes tu propio trabajo contra `QUALITY-GATES.md`: repórtalo explícitamente en el Pull Request para que un CODEOWNER lo revise.

## 9. Flujo de trabajo esperado

```
rama (según GIT-STANDARD.md)
  → cambio en la capa correspondiente
    → estándar aplicable de docs/standards/ respetado
      → pruebas (unit/integration/e2e según corresponda, ver tests/)
        → documentación actualizada (README de capa, ADR si aplica, CHANGELOG)
          → Pull Request con checklist de QUALITY-GATES.md completado
            → revisión de CODEOWNERS
              → merge según estrategia de GIT-STANDARD.md
```

## 10. Qué NO debe hacer Claude en este repositorio

- No implementar lógica de negocio de una aplicación concreta (TicketGateway, Portal NOC, etc.) dentro de TEAF; este repositorio es solo el framework.
- No tomar decisiones estructurales o de stack sin ADR y sin aprobación explícita del usuario.
- No introducir dependencias, librerías o servicios externos no aprobados en [STACK.md](docs/architecture/STACK.md).
- No deshabilitar, saltar o debilitar tests, lint o quality gates para "hacer pasar" un cambio.
- No commitear secretos, credenciales ni datos sensibles (ver [SECURITY-STANDARD.md](docs/standards/SECURITY-STANDARD.md)).
- No reorganizar carpetas, renombrar capas o alterar la arquitectura documentada sin aprobación explícita — ver sección 12.
- No avanzar a una siguiente versión/sprint del [ROADMAP.md](docs/roadmap/ROADMAP.md) sin que el usuario lo apruebe explícitamente.
- No generar documentación duplicada: si un contenido ya existe en otro documento, enlázalo en vez de repetirlo.

## 11. Cómo deben desarrollarse nuevas funcionalidades

1. Verifica en [MODULE-CATALOG.md](docs/architecture/MODULE-CATALOG.md) si el módulo ya existe o está planeado.
2. Parte de la plantilla correspondiente en [`/templates/`](templates/README.md) (`api-template.md`, `service-template.md`, `repository-template.md`, etc.).
3. Ubica cada pieza en su capa correcta según [ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md) — nunca mezcles responsabilidades de capas distintas en un mismo archivo.
4. Cumple el/los estándar(es) aplicables de la tabla de la sección 7.
5. Añade pruebas conforme a [CODING-STANDARD.md](docs/standards/CODING-STANDARD.md) y a la pirámide descrita en [`tests/README.md`](tests/README.md).
6. Actualiza `MODULE-CATALOG.md` (si aplica) y `CHANGELOG.md`.

## 12. Cómo deben proponerse cambios de arquitectura

1. Cambios pequeños dentro de los patrones existentes: se implementan directamente siguiendo los estándares vigentes, sin ADR.
2. Cambios estructurales (nueva tecnología, nuevo principio, cambio de capa o patrón, impacto en todas las aplicaciones futuras): se abre primero un issue con [`.github/ISSUE_TEMPLATE/architecture_change.md`](.github/ISSUE_TEMPLATE/architecture_change.md) o, si el cambio es extenso, se redacta [`/templates/architecture-change-proposal-template.md`](templates/architecture-change-proposal-template.md).
3. Solo tras la aprobación explícita de la propuesta se redacta el ADR formal (sección 13) y se implementa el cambio.
4. Claude nunca implementa un cambio arquitectónico estructural sin haber completado este flujo.

## 13. Cómo documentar nuevas decisiones (ADR)

1. Copia [`/templates/adr-template.md`](templates/adr-template.md) y numéralo consecutivamente (`ADR-006`, `ADR-007`, ...) dentro de `docs/architecture/adr/`.
2. Completa Estado, Contexto, Problema, Decisión y Consecuencias (positivas y negativas), siguiendo el mismo nivel de detalle que ADR-001 a ADR-005.
3. Actualiza el índice en [`docs/architecture/adr/README.md`](docs/architecture/adr/README.md).
4. Solo un ADR en estado "Aceptado" habilita la implementación del cambio que describe.

## 14. Cómo crear nuevos módulos

1. Define el módulo en [`docs/architecture/MODULE-CATALOG.md`](docs/architecture/MODULE-CATALOG.md) (objetivo, dependencias, versión objetivo, nivel de reutilización, prioridad) antes de crear código.
2. Sigue el checklist y árbol de carpetas de [`/templates/module-template.md`](templates/module-template.md).
3. Cada carpeta nueva incluye su propio `README.md` de responsabilidad, siguiendo el mismo estilo que los ya existentes en `teaf/_internal/*/README.md` y `frontend/src/*/README.md`.
4. Si el módulo introduce una épica/feature nueva, añádela a [`docs/roadmap/BACKLOG.md`](docs/roadmap/BACKLOG.md).

## 15. Checklist antes de cada Pull Request

Versión condensada de [QUALITY-GATES.md](docs/standards/QUALITY-GATES.md) — el documento completo es la fuente de verdad:

- [ ] Respeta la capa y dirección de dependencias de la arquitectura.
- [ ] Cumple el/los estándar(es) de `docs/standards/` aplicables al cambio.
- [ ] Incluye pruebas para el comportamiento nuevo o modificado.
- [ ] Documentación actualizada (README de capa, ADR si aplica).
- [ ] `CHANGELOG.md` actualizado en `[Unreleased]`.
- [ ] `docs/roadmap/BACKLOG.md` y `docs/architecture/MODULE-CATALOG.md` actualizados si el cambio los afecta.
- [ ] Sin secretos ni credenciales en el diff.
- [ ] Sigue la convención de commits y de ramas de [GIT-STANDARD.md](docs/standards/GIT-STANDARD.md).
