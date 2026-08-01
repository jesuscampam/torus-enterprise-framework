# Estándar de Código — TEAF

Este documento define las convenciones de estilo, estructura y calidad de código obligatorias para todo el código escrito dentro de TEAF, en cumplimiento de los principios SOLID, DRY y KISS.

## 1. Backend (Python)

- Se sigue **PEP 8** como base de estilo, reforzado por formateo automático con **black** y linting con **ruff**.
- **Type hints obligatorios** en toda función, método y variable de módulo pública; el framework asume tipado estricto verificado con **mypy**.
- Longitud de línea: 100 caracteres.
- Imports ordenados y agrupados (estándar de librería → terceros → internos), sin imports circulares entre capas (ver `docs/architecture/ARCHITECTURE.md`, dirección de dependencias).
- Nombres: `snake_case` para funciones/variables, `PascalCase` para clases, `UPPER_SNAKE_CASE` para constantes.
- Funciones y métodos con una única responsabilidad clara; si una función supera ~40 líneas o mezcla niveles de abstracción distintos, se descompone.

## 2. Frontend (TypeScript / React)

- **TypeScript estricto** (`strict: true`); se prohíbe `any` salvo justificación explícita en comentario.
- Formateo con **prettier**, linting con **eslint** (configuración basada en reglas recomendadas de React + TypeScript).
- Componentes funcionales con hooks; se prohíben componentes de clase salvo integración con librerías legadas que lo exijan.
- Nombres: `PascalCase` para componentes (`IncidentTable.tsx`), `camelCase` para funciones/variables/hooks (`useIncidentList`), un componente por archivo.
- Props tipadas explícitamente mediante `interface` o `type`, nunca `any` ni props implícitas.

## 3. Principios de diseño aplicados

- **SOLID**: cada clase/módulo tiene una única razón para cambiar (SRP); las dependencias se inyectan por interfaz, no se instancian directamente (DIP) — ver `core/` y Repository Pattern.
- **DRY**: la duplicación de lógica de negocio o de acceso a datos entre módulos es motivo de bloqueo en revisión; la duplicación incidental de 2-3 líneas no justifica una abstracción prematura (ver KISS).
- **KISS**: no se introduce una abstracción, patrón o capa adicional sin una necesidad concreta y actual; no se diseña para requisitos hipotéticos futuros.
- No se añade manejo de errores, validación o configuración para escenarios que no pueden ocurrir dado el contrato ya validado por capas anteriores (por ejemplo, `services/` no revalida lo que `schemas/` ya garantizó).

## 4. Estructura y capas

- Todo código nuevo respeta la capa a la que pertenece según `docs/architecture/ARCHITECTURE.md`; no se implementa lógica de negocio en `api/` ni acceso a datos fuera de `repository/`.
- No se crean nuevas carpetas de primer nivel dentro de `backend/` o `frontend/src/` sin que la necesidad esté documentada (ADR si es estructural).

## 5. Convención de commits

Se usa [Conventional Commits](https://www.conventionalcommits.org/): `tipo(alcance): descripción`. Tipos válidos: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `build`, `ci`, `perf`. Detalle completo del flujo en [CONTRIBUTING.md](../../CONTRIBUTING.md).

## 6. Estrategia de branching

Trunk-based development: `main` protegida y siempre desplegable; ramas de trabajo de corta duración (`feature/*`, `fix/*`, `docs/*`) que se integran vía Pull Request revisado.

## 7. Testing

- Todo caso de uso en `services/` requiere pruebas unitarias con dependencias (`repository/`) dobladas (mocks/fakes).
- Toda ruta de `api/` con lógica de validación o autorización no trivial requiere prueba de integración.
- Los flujos críticos de negocio de extremo a extremo (una vez existan aplicaciones sobre TEAF) requieren pruebas e2e.
- Cobertura mínima objetivo: 80% en `services/` y `repository/`, capas donde reside la lógica de mayor riesgo. La cobertura no es un fin en sí mismo: una prueba que no verifica comportamiento real no cuenta como cumplimiento del estándar.
- Estructura de pruebas alineada con `tests/unit/`, `tests/integration/`, `tests/e2e/` (ver READMEs correspondientes).

## 8. Comentarios y documentación en código

- El código se documenta a través de nombres claros; los comentarios solo se usan para explicar el **por qué** de una decisión no evidente (una restricción externa, un workaround temporal, una invariante no obvia), nunca para describir **qué** hace el código.
- No se dejan comentarios de código muerto, TODOs sin issue asociado, ni bloques comentados en el historial permanente.

## 9. Checklist de revisión de código

Antes de aprobar un Pull Request, el revisor verifica:

- [ ] El cambio respeta la capa y dirección de dependencias de la arquitectura.
- [ ] No introduce duplicación evitable ni abstracciones innecesarias.
- [ ] Incluye pruebas para el comportamiento nuevo o modificado.
- [ ] Cumple el estándar de la capa afectada (`API-STANDARD.md`, `DATABASE-STANDARD.md`, `SECURITY-STANDARD.md`, `LOGGING-STANDARD.md`, según corresponda).
- [ ] No contiene secretos, credenciales ni datos sensibles.
