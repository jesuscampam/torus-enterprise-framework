# Extensibilidad — TEAF

Cómo el framework crece sin romper compatibilidad: crear, extender, registrar y versionar módulos, reemplazar implementaciones, y añadir proveedores y conectores nuevos. Complementa [FRAMEWORK-BLUEPRINT.md, sección 12](FRAMEWORK-BLUEPRINT.md#12-evolución-del-framework) con el detalle operativo que allí se resume.

## 1. Cómo crear módulos

1. Verifica en [MODULE-CATALOG.md](MODULE-CATALOG.md) y en el [Decision Tree](DECISION-TREE.md#6-cuándo-crear-un-nuevo-módulo) que la responsabilidad no la cubre ya un módulo existente.
2. Completa la ficha de [`/templates/module-template.md`](../../templates/module-template.md): objetivo, capas involucradas, dependencias, versión objetivo, nivel de reutilización.
3. Da de alta el módulo en `MODULE-CATALOG.md` **antes** de crear una sola carpeta.
4. Actualiza [`dependency-map.mmd`](../diagrams/dependency-map.mmd) y [`module-map.mmd`](../diagrams/module-map.mmd) con el módulo nuevo y sus dependencias declaradas.
5. Solo entonces se crea la estructura de carpetas, cada una con su `README.md` de responsabilidad.

## 2. Cómo extender módulos existentes

- **Preferir extensión sobre creación**: si la necesidad encaja en la responsabilidad de un módulo existente, se añade allí — no se crea un módulo paralelo con responsabilidad solapada.
- Toda extensión respeta la interfaz pública ya aceptada del módulo (por ejemplo, añadir un método a la interfaz de `repository/` es una extensión; cambiar la firma de uno existente es una ruptura, ver sección 4).
- Una extensión que introduce una dependencia nueva debe verificarse contra las [Reglas de Dependencias](FRAMEWORK-BLUEPRINT.md#6-reglas-de-dependencias) antes de implementarse.

## 3. Cómo registrar módulos

TEAF no tiene (todavía) un mecanismo de registro en runtime — el "registro" de un módulo hoy es documental:

1. Fila en `MODULE-CATALOG.md` (fuente de verdad de qué módulos existen y su estado).
2. Nodo en `module-map.mmd` y `dependency-map.mmd`.
3. A partir de la Versión 1 del [roadmap](../roadmap/ROADMAP.md), el registro documental se complementa con el registro real en el contenedor de Dependency Injection de `core/` (cada módulo expone sus dependencias inyectables). Este blueprint no implementa ese mecanismo; lo deja preparado como siguiente paso natural.

## 4. Cómo versionar módulos

- TEAF versiona el framework completo con SemVer (ver [GIT-STANDARD.md](../standards/GIT-STANDARD.md), sección 6), no cada módulo de forma independiente.
- Un cambio en la interfaz pública de un módulo (`repository/`, `ai/`, `schemas/`, etc.) que rompe a sus consumidores es `MAJOR` — se documenta con `BREAKING CHANGE` en el commit y, si afecta a `api/`, sigue la política de versionado de [API-STANDARD.md](../standards/API-STANDARD.md) (`/api/v2`).
- Añadir una capacidad nueva sin romper nada existente (por ejemplo, un `Provider` de IA nuevo) es `MINOR`.

## 5. Cómo reemplazar implementaciones

El patrón se repite en todo el framework: **interfaz estable + implementaciones intercambiables**.

| Módulo | Interfaz estable | Implementación reemplazable |
|---|---|---|
| Repository | Contrato de `repository/` | Implementación SQLAlchemy sobre PostgreSQL (podría sustituirse sin tocar `services/`) |
| AI | Interfaz de cliente LLM de `ai/` | `Provider` concreto: OpenAI, Azure OpenAI, Anthropic, Gemini, Ollama (ver [`ai-provider-architecture.mmd`](../diagrams/ai-provider-architecture.mmd)) |
| Scheduler | Interfaz de `scheduler/` | Motor de ejecución concreto (cron interno, cola distribuida, etc.) |
| Webhooks | Interfaz de `webhooks/` | Conector concreto (SAP, Salesforce, Control-M) |

Reemplazar una implementación **nunca** requiere cambios en `services/` ni en capas superiores — si los requiere, la interfaz no estaba bien diseñada y el cambio de interfaz sí es un cambio `MAJOR` (sección 4).

## 6. Cómo agregar nuevos proveedores de IA

1. Implementa la interfaz de cliente LLM (y, si aplica, de embeddings) definida en `teaf/_internal/ai/`.
2. Ubica la implementación dentro del subgrafo `Providers` de [`ai-provider-architecture.mmd`](../diagrams/ai-provider-architecture.mmd) — actualiza el diagrama.
3. No requiere ADR si respeta la interfaz ya aceptada; sí lo requiere si el proveedor exige cambiar la interfaz misma (por ejemplo, un modelo de function calling incompatible con el contrato actual).
4. El proveedor se selecciona vía `config/` por entorno — nunca hardcodeado en `services/`.

## 7. Cómo agregar nuevos conectores

1. Todo conector (SAP, Salesforce, Control-M u otro sistema futuro) se implementa sobre `teaf/_internal/webhooks/`, dependiente de `Security` (y de `Scheduler` si requiere polling periódico — ver dependencia de Control-M Connector en [MODULE-CATALOG.md](MODULE-CATALOG.md)).
2. Da de alta el conector en `MODULE-CATALOG.md` antes de implementarlo, siguiendo el mismo proceso que cualquier módulo nuevo (sección 1).
3. Un conector nunca accede a `Database` directamente ni contiene lógica de negocio de una integración concreta más allá de la traducción del payload externo (ver `teaf/_internal/webhooks/README.md`).

## 8. Cómo mantener compatibilidad

- Ninguna interfaz pública (`repository/`, `ai/`, `schemas/`, contratos de `api/`) cambia de forma incompatible sin pasar por el ciclo `MAJOR` de la sección 4.
- Toda deprecación se anuncia explícitamente (en `CHANGELOG.md` y, si aplica, en la documentación OpenAPI) con un período de convivencia antes de retirarse — igual que ya exige [API-STANDARD.md](../standards/API-STANDARD.md) para versiones de API.
- Los tests de integración de un módulo actúan como contrato ejecutable: si cambian sin que cambie el número de versión `MAJOR`, es una señal de que se rompió compatibilidad sin declararlo.

## 9. Buenas prácticas de extensibilidad

- Preferir composición e interfaces sobre herencia profunda.
- Una nueva capacidad nunca se implementa "temporalmente" saltándose una capa (por ejemplo, un conector que hable directo con `database/` para "ir más rápido") — eso genera deuda arquitectónica invisible.
- Todo módulo nuevo o extendido pasa por el [Architecture Review Checklist](FRAMEWORK-BLUEPRINT.md#14-architecture-review-checklist) antes de fusionarse.
- Documentar primero, implementar después — igual que el resto del framework (API First aplicado también a la extensibilidad interna).
