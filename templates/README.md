# Plantillas — TEAF

Plantillas reutilizables para acelerar el desarrollo de nuevas piezas del framework y de las aplicaciones que se construyan sobre él, manteniendo consistencia con [docs/architecture/ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md) y los estándares de `docs/standards/`.

> Todas las plantillas son archivos Markdown (`.md`) con bloques de código **ilustrativos**. Ningún archivo de esta carpeta se ejecuta, se importa ni forma parte de la aplicación: son patrones de referencia para copiar y adaptar al crear código real a partir de la Versión 1 del [roadmap](../docs/roadmap/ROADMAP.md).

## Índice

| Plantilla | Úsala cuando... |
|---|---|
| [`module-template.md`](module-template.md) | Vas a dar de alta un módulo nuevo del framework (ver [MODULE-CATALOG.md](../docs/architecture/MODULE-CATALOG.md)). |
| [`api-template.md`](api-template.md) | Vas a crear un router/endpoint nuevo en `backend/api/`. |
| [`repository-template.md`](repository-template.md) | Vas a crear un repositorio nuevo en `backend/repository/`. |
| [`service-template.md`](service-template.md) | Vas a crear un caso de uso nuevo en `backend/services/`. |
| [`database-migration-template.md`](database-migration-template.md) | Vas a crear una migración Alembic en `database/migrations/`. |
| [`react-component-template.md`](react-component-template.md) | Vas a crear un componente nuevo en `frontend/src/components/` o `frontend/src/pages/`. |
| [`issue-template.md`](issue-template.md) | Vas a redactar una historia/issue detallada para el backlog. |
| [`adr-template.md`](adr-template.md) | Vas a documentar una decisión arquitectónica aceptada. |
| [`architecture-change-proposal-template.md`](architecture-change-proposal-template.md) | Vas a proponer un cambio arquitectónico **antes** de que se convierta en ADR. |

## Relación entre `adr-template.md` y `architecture-change-proposal-template.md`

Son dos etapas distintas del mismo proceso (ver [CLAUDE.md](../CLAUDE.md), sección 12):

1. **Propuesta** (`architecture-change-proposal-template.md`): documento de discusión, con opciones evaluadas y trade-offs, usado para decidir.
2. **ADR** (`adr-template.md`): registro formal de la decisión ya tomada, una vez aprobada la propuesta.
