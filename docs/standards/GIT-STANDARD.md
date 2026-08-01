# Estándar de Git — TEAF

Este documento es la fuente canónica de la estrategia de ramas, commits, Pull Requests, merge y versionado de TEAF. `CONTRIBUTING.md` y `CODING-STANDARD.md` enlazan aquí en vez de duplicar esta política.

## 1. Modelo de ramas (Git Flow simplificado)

TEAF usa una variante ligera de Git Flow, adecuada a un framework con ciclos de release explícitos (versiones V1-V5 del [roadmap](../roadmap/ROADMAP.md)):

| Rama | Propósito | Protegida | Vida |
|---|---|---|---|
| `main` | Código estable, siempre desplegable. Refleja la última versión liberada. | Sí | Permanente |
| `develop` | Rama de integración de las próximas funcionalidades hacia la siguiente versión. | Sí | Permanente |
| `feature/*` | Desarrollo de una funcionalidad o historia concreta, sobre `develop`. | No | Corta duración |
| `release/*` | Estabilización de una versión antes de fusionarla a `main` (freeze de alcance, solo fixes). | No | Corta duración |
| `hotfix/*` | Corrección urgente directamente sobre `main`, para un defecto crítico en producción. | No | Muy corta duración |

```
feature/*  ──┐
             ├──►  develop  ──►  release/*  ──►  main  ──►  (tag vX.Y.Z)
feature/*  ──┘                                     ▲
                                    hotfix/* ───────┘  (y se reincorpora a develop)
```

### Reglas

- Toda `feature/*` nace de `develop` y se fusiona de vuelta a `develop` vía Pull Request.
- Ninguna `feature/*` se fusiona directamente a `main`.
- `release/*` nace de `develop` cuando el alcance de una versión está congelado; solo admite correcciones, no nuevas funcionalidades.
- `hotfix/*` nace de `main`, se fusiona a `main` (con tag de nueva versión de parche) y se reincorpora a `develop` para no perder la corrección.

## 2. Naming convention de ramas

```
<tipo>/<descripcion-corta-en-kebab-case>
```

| Tipo | Ejemplo |
|---|---|
| `feature/` | `feature/repository-pattern-base` |
| `fix/` | `fix/jwt-refresh-expiry` |
| `docs/` | `docs/logging-standard` |
| `release/` | `release/v1.0.0` |
| `hotfix/` | `hotfix/security-token-leak` |
| `chore/` | `chore/update-dependabot-config` |

No se usan nombres genéricos (`fix`, `update`, `wip`) ni iniciales de persona.

## 3. Convención de commits

[Conventional Commits](https://www.conventionalcommits.org/), ya introducida en [CODING-STANDARD.md](CODING-STANDARD.md):

```
<tipo>(<alcance opcional>): <descripción breve en imperativo>

[cuerpo opcional explicando el porqué, no el qué]

[footer opcional: BREAKING CHANGE, referencias a issues]
```

Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`.

```
feat(security): implementar rotación de refresh tokens
fix(repository): corregir fuga de sesión en UnitOfWork
docs(architecture): agregar ADR-006 sobre estrategia de multi-tenancy

BREAKING CHANGE: el contrato de AuthService.refresh() cambia de firma.
```

Un commit con `BREAKING CHANGE` en el footer, o con `!` tras el tipo (`feat!:`), señala un cambio incompatible — relevante para el versionado (sección 6).

## 4. Pull Requests

- Título con la misma convención que los commits.
- Un PR aborda un único propósito; no mezcla refactors no relacionados con la funcionalidad principal.
- Toda `feature/*` hacia `develop` requiere al menos una aprobación de un CODEOWNER (ver [`.github/CODEOWNERS`](../../.github/CODEOWNERS)).
- Todo PR de `release/*` hacia `main` requiere aprobación explícita adicional, dado que dispara una nueva versión pública del framework.
- El checklist de [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md) y los criterios de [QUALITY-GATES.md](QUALITY-GATES.md) deben cumplirse antes de solicitar revisión.

## 5. Estrategia de merge

| Origen → Destino | Estrategia | Motivo |
|---|---|---|
| `feature/*` → `develop` | Squash merge | Historial de `develop` limpio, un commit por funcionalidad. |
| `release/*` → `main` | Merge commit (no squash) | Preserva la trazabilidad completa de la versión liberada. |
| `release/*` → `develop` | Merge commit | Reincorpora los fixes de estabilización a la rama de integración. |
| `hotfix/*` → `main` y → `develop` | Merge commit | Trazabilidad de la corrección urgente en ambas ramas. |

No se usa `rebase` sobre ramas compartidas (`main`, `develop`) bajo ninguna circunstancia.

## 6. Versionado Semántico (SemVer)

TEAF versiona sus releases como `MAJOR.MINOR.PATCH`:

- **MAJOR**: cambio incompatible en un contrato del framework (ver `BREAKING CHANGE` en commits) — por ejemplo, una firma de `services/` o un contrato de `schemas/` que rompe a consumidores existentes.
- **MINOR**: nueva funcionalidad compatible hacia atrás — por ejemplo, un módulo nuevo del [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md).
- **PATCH**: corrección de defecto compatible hacia atrás.

Cada versión liberada en `main` se marca con un tag `vMAJOR.MINOR.PATCH` y se documenta en [`CHANGELOG.md`](../../CHANGELOG.md) siguiendo Keep a Changelog. Las versiones V1-V5 del [roadmap](../roadmap/ROADMAP.md) son hitos de alcance, no equivalen 1 a 1 con versiones SemVer — una versión del roadmap puede liberarse como una o varias versiones `MINOR` sucesivas.

## 7. Resumen del flujo recomendado

```
1. Crear feature/<descripcion> desde develop.
2. Commits siguiendo Conventional Commits.
3. Abrir PR hacia develop, completar checklist de QUALITY-GATES.md.
4. Revisión y aprobación de CODEOWNER → squash merge.
5. Al congelar el alcance de una versión: release/vX.Y.Z desde develop.
6. Solo fixes en release/*; al estabilizar, merge a main (tag vX.Y.Z) y de vuelta a develop.
7. Ante un defecto crítico en producción: hotfix/* desde main, merge a main y develop.
```
