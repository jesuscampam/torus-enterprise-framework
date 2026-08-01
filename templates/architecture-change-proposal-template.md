# Plantilla — Propuesta de cambio arquitectónico

> PLANTILLA — úsala **antes** de redactar un ADR formal, cuando el cambio propuesto es lo bastante grande o incierto como para necesitar discusión previa. Ver [CLAUDE.md](../CLAUDE.md), sección 12, y el issue corto equivalente en [`.github/ISSUE_TEMPLATE/architecture_change.md`](../.github/ISSUE_TEMPLATE/architecture_change.md).

## Cómo usar esta plantilla

1. Completa todas las secciones antes de pedir revisión.
2. Si la propuesta se aprueba, su contenido se resume y formaliza como un nuevo ADR usando [`adr-template.md`](adr-template.md) — esta plantilla **no reemplaza** al ADR, lo precede.
3. Si se rechaza, se archiva igualmente (con el motivo del rechazo) para no repetir la discusión sin contexto en el futuro.

---

## Título de la propuesta

`{{Título breve y descriptivo}}`

## Problema u oportunidad

<Qué limitación actual del framework motiva esta propuesta. Cuantifica el impacto si es posible.>

## Opciones evaluadas

| Opción | Descripción | Ventajas | Desventajas |
|---|---|---|---|
| A | <opción 1> | | |
| B | <opción 2> | | |
| C (statu quo) | No cambiar nada | | |

## Opción recomendada

<Cuál de las anteriores se recomienda y por qué.>

## Impacto

- **Capas/módulos afectados**: <api/, services/, repository/, un módulo de `MODULE-CATALOG.md`, etc.>
- **Aplicaciones futuras afectadas**: <todas / algunas / ninguna todavía>
- **Compatibilidad hacia atrás**: <rompe algo existente? requiere migración?>
- **Esfuerzo estimado**: <Alto / Medio / Bajo>

## Quién debe aprobar

<CODEOWNER(s) o stakeholder(s) cuya aprobación explícita se requiere antes de implementar.>

## Siguiente paso si se aprueba

Redactar `ADR-XXX` a partir de [`adr-template.md`](adr-template.md) resumiendo la decisión final tomada aquí.
