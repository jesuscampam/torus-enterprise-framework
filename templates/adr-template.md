# Plantilla — ADR (Architecture Decision Record)

> PLANTILLA — copia este archivo dentro de `docs/architecture/adr/` como `ADR-XXX-titulo-corto.md`, numerado consecutivamente. Estructura idéntica a la usada en ADR-001 a ADR-005. Ver [CLAUDE.md](../CLAUDE.md), sección 13, y el índice en [`docs/architecture/adr/README.md`](../docs/architecture/adr/README.md).

---

# ADR-XXX: <Título de la decisión>

## Estado

Propuesto | Aceptado | Rechazado | Reemplazado por ADR-YYY | Obsoleto

## Contexto

<Situación previa a la decisión: qué existía, qué necesidad o limitación motiva evaluar un cambio. Debe ser suficiente para que alguien sin contexto previo entienda por qué se está decidiendo algo.>

## Problema

<Pregunta concreta y accionable que esta decisión responde. Una sola pregunta, no una lista de problemas dispares.>

## Decisión

<Qué se decidió, de forma explícita y accionable. Incluye los motivos determinantes, no solo el resultado.>

## Consecuencias

### Positivas

- <Consecuencia positiva 1>
- <Consecuencia positiva 2>

### Negativas / Trade-offs

- <Qué se sacrifica o qué riesgo se acepta conscientemente>
- <Qué disciplina adicional exige esta decisión al equipo>

---

## Checklist antes de marcar como "Aceptado"

- [ ] Se evaluaron y descartaron explícitamente al menos una alternativa.
- [ ] El índice `docs/architecture/adr/README.md` está actualizado con la nueva fila.
- [ ] Si reemplaza un ADR anterior, ese ADR se marcó como "Reemplazado por ADR-XXX".
- [ ] Si introduce una tecnología nueva, `docs/architecture/STACK.md` se actualiza en consecuencia.
