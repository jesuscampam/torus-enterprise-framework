# Quality Gates — TEAF

Criterios mínimos, no negociables, que cualquier cambio debe cumplir antes de fusionarse al framework. Un Pull Request que no cumpla alguno de estos criterios se bloquea hasta resolverlo — no se hacen excepciones "por esta vez" (ver [CLAUDE.md](../../CLAUDE.md), sección 10).

Estos gates se verifican **a nivel de PR/cambio al framework**. Para el criterio de "una historia/feature está terminada", ver [DEFINITION-OF-DONE.md](DEFINITION-OF-DONE.md), que es más granular.

## 1. Cobertura de pruebas

- `services/` y `repository/` mantienen cobertura ≥ 80% (umbral de [CODING-STANDARD.md](CODING-STANDARD.md), sección 7).
- Ninguna prueba se marca como `skip`/`xfail` sin una justificación documentada y un issue de seguimiento.

## 2. Lint y type-checking

- Backend: `ruff` y `mypy` en verde, formateo `black` aplicado.
- Frontend: `eslint` y `tsc --strict` en verde, formateo `prettier` aplicado.

## 3. Documentación

- Toda capa/carpeta afectada por el cambio tiene su `README.md` actualizado si su responsabilidad cambió.
- Si el cambio introduce o modifica un endpoint, la documentación OpenAPI/Swagger generada refleja el cambio (ver punto 9).

## 4. ADR actualizado

- Si el cambio implica una decisión arquitectónica (ver criterios en [CLAUDE.md](../../CLAUDE.md), sección 12), existe un ADR en estado "Aceptado" que la respalda **antes** de fusionar el código que la implementa.

## 5. Roadmap y backlog actualizados

- [`docs/roadmap/BACKLOG.md`](../roadmap/BACKLOG.md) refleja el estado real de la historia (completada, bloqueada, replanificada).
- [`docs/architecture/MODULE-CATALOG.md`](../architecture/MODULE-CATALOG.md) se actualiza si el cambio crea, elimina o cambia el estado de un módulo.

## 6. Changelog actualizado

- Todo cambio visible (nueva capacidad, cambio de comportamiento, nuevo estándar) se añade a [`CHANGELOG.md`](../../CHANGELOG.md) bajo `[Unreleased]`, siguiendo Keep a Changelog.

## 7. Sin secretos en el código

- Escaneo de secretos en verde (credenciales, tokens, claves privadas).
- Ninguna variable de entorno sensible con valor por defecto hardcodeado fuera de `.env.example`.

## 8. Docker funcionando

- La imagen del componente afectado construye sin error (`docker build`).
- El contenedor arranca y responde correctamente en `docker-compose` local.

## 9. Health Check funcionando

- El endpoint `/health` (y `/ready` si aplica) responde `200 OK` tras el cambio, en local y en el entorno de CI.

## 10. Swagger/OpenAPI actualizado

- Todo endpoint nuevo o modificado en `backend/api/` está documentado en el esquema OpenAPI generado (resumen, ejemplos, códigos de error), conforme a [API-STANDARD.md](API-STANDARD.md).

## 11. Checklist de revisión humana

Además de los checks automatizados anteriores, el revisor (CODEOWNER) verifica manualmente:

- [ ] El cambio respeta la dirección de dependencias entre capas (ver [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)).
- [ ] No introduce una tecnología fuera de [STACK.md](../architecture/STACK.md) sin ADR.
- [ ] No introduce complejidad o abstracción innecesaria (KISS/DRY, ver [CODING-STANDARD.md](CODING-STANDARD.md)).
- [ ] La rama y los commits siguen [GIT-STANDARD.md](GIT-STANDARD.md).
- [ ] El PR completa el checklist de [`.github/PULL_REQUEST_TEMPLATE.md`](../../.github/PULL_REQUEST_TEMPLATE.md).

## Excepciones

No existen excepciones permanentes a estos gates. Una excepción temporal (por ejemplo, un gate no aplicable porque el componente Docker/health-check aún no existe en esta fase del framework) debe declararse explícitamente en la descripción del PR, indicando por qué no aplica todavía.
