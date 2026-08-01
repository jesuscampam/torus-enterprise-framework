# Definition of Done — TEAF

Criterios que determinan cuándo una **historia o funcionalidad** (no un PR aislado — ver la distinción con [QUALITY-GATES.md](QUALITY-GATES.md)) puede considerarse terminada dentro de TEAF. Una historia del [BACKLOG.md](../roadmap/BACKLOG.md) no se marca como completada si no cumple **todos** los criterios aplicables.

## Criterios técnicos

- [ ] La funcionalidad está implementada en la(s) capa(s) correcta(s) según [ARCHITECTURE.md](../architecture/ARCHITECTURE.md), sin violar la dirección de dependencias.
- [ ] Cumple el/los estándar(es) aplicables (`API-STANDARD.md`, `DATABASE-STANDARD.md`, `SECURITY-STANDARD.md`, `LOGGING-STANDARD.md`, según la capa tocada).
- [ ] No introduce deuda técnica no documentada (si se acepta deuda técnica consciente, se registra como issue de seguimiento).
- [ ] Funciona de extremo a extremo en el entorno de desarrollo local (Docker Compose), no solo en aislamiento.

## Criterios de documentación

- [ ] El `README.md` de cada carpeta/capa afectada refleja la responsabilidad real tras el cambio.
- [ ] Si la funcionalidad introduce un módulo nuevo, está dado de alta en [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md).
- [ ] Si la funcionalidad implica una decisión arquitectónica, existe un ADR "Aceptado" que la respalda.
- [ ] `CHANGELOG.md` actualizado.

## Criterios de pruebas

- [ ] Pruebas unitarias para la lógica de `services/`/`repository/` involucrada.
- [ ] Pruebas de integración si la funcionalidad cruza capas de forma no trivial (por ejemplo, autenticación + persistencia).
- [ ] Pruebas e2e si la funcionalidad forma parte de un flujo crítico ya cubierto por la estrategia de `tests/e2e/`.
- [ ] Los criterios de aceptación de la historia (ver [`/templates/issue-template.md`](../../templates/issue-template.md)) están todos verificados, no solo "código escrito".

## Criterios de seguridad

- [ ] Si la funcionalidad maneja datos sensibles o autenticación/autorización, cumple [SECURITY-STANDARD.md](SECURITY-STANDARD.md) en su totalidad.
- [ ] No introduce secretos en el código ni en archivos versionados.
- [ ] Las entradas externas están validadas mediante `schemas/` (si aplica).

## Criterios de revisión

- [ ] Pull Request aprobado por al menos un CODEOWNER.
- [ ] Todos los [QUALITY-GATES.md](QUALITY-GATES.md) del cambio están en verde.
- [ ] La historia correspondiente en [BACKLOG.md](../roadmap/BACKLOG.md) se actualiza a "Completada" (o al estado equivalente) solo después de que el PR se fusiona.

## Qué NO es "Done"

- Código que compila pero no tiene pruebas.
- Una funcionalidad documentada pero sin verificación de que cumple sus criterios de aceptación.
- Un cambio fusionado sin actualizar `CHANGELOG.md`, `MODULE-CATALOG.md` o `BACKLOG.md` cuando correspondía.
