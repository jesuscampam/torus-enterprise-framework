# Architecture Decision Records (ADR)

Este directorio contiene los registros de decisiones arquitectónicas de TEAF. Un ADR documenta una decisión estructural significativa: por qué se tomó, qué alternativas se descartaron y qué consecuencias — positivas y negativas — se aceptan.

## Cuándo crear un ADR

Crea un ADR cuando la decisión:

- Introduce o reemplaza una tecnología del stack oficial.
- Cambia un patrón estructural del framework (capas, flujo de dependencias, estrategia de persistencia, etc.).
- Adopta o modifica un principio arquitectónico transversal (seguridad, observabilidad, configuración, IA).
- Tiene impacto en todas las aplicaciones futuras construidas sobre TEAF.

No crees un ADR para decisiones de implementación local que no afecten al framework en su conjunto (esas se documentan, si acaso, en el PR correspondiente).

## Índice

| ADR | Título | Estado |
|---|---|---|
| [ADR-001](ADR-001-uso-de-fastapi.md) | Uso de FastAPI | Aceptado |
| [ADR-002](ADR-002-uso-de-postgresql.md) | Uso de PostgreSQL | Aceptado |
| [ADR-003](ADR-003-uso-de-docker.md) | Uso de Docker | Aceptado |
| [ADR-004](ADR-004-api-first.md) | API First | Aceptado |
| [ADR-005](ADR-005-cloud-ready.md) | Cloud Ready | Aceptado |
| [ADR-006](ADR-006-internal-namespace-refactor.md) | Internal Namespace Refactor | Aceptado |
| [ADR-007](ADR-007-enterprise-security-stack.md) | Enterprise Security Stack | Aceptado |

## Plantilla

Todo ADR nuevo debe numerarse consecutivamente (`ADR-006`, `ADR-007`, ...) y seguir esta estructura:

```markdown
# ADR-XXX: <Título de la decisión>

## Estado

Propuesto | Aceptado | Rechazado | Reemplazado por ADR-YYY | Obsoleto

## Contexto

<Situación previa a la decisión: qué existía, qué se necesitaba resolver.>

## Problema

<Pregunta concreta que esta decisión responde.>

## Decisión

<Qué se decidió, de forma explícita y accionable.>

## Consecuencias

### Positivas

- ...

### Negativas / Trade-offs

- ...
```
