# `benchmarks/` — suite de rendimiento de TEAF

Mide el coste de las operaciones que **toda** aplicación construida sobre TEAF paga, arranque
tras arranque y petición tras petición. No mide lógica de negocio: eso pertenece a cada
aplicación, no al framework.

Introducida en Sprint 2.9.1 ([CHANGELOG.md](../CHANGELOG.md)) junto con la baseline documentada
en [docs/BENCHMARKS.md](../docs/BENCHMARKS.md), que es donde viven los números y su
interpretación. Este README describe la herramienta; el documento describe los resultados.

## Uso

```bash
python -m benchmarks                      # ejecuta todo y compara con la baseline
python -m benchmarks --suite di events    # solo esas suites
python -m benchmarks --save-baseline      # fija los resultados actuales como referencia
python -m benchmarks --json salida.json   # vuelca los resultados sin tocar la baseline
python -m benchmarks --no-compare         # mide sin evaluar regresiones
```

Se ejecuta también como una puerta de calidad más: `python scripts/quality_gates.py`
(ver [docs/standards/QUALITY-GATES.md](../docs/standards/QUALITY-GATES.md)).

## Contenido

| Archivo | Responsabilidad |
|---|---|
| `harness.py` | Instrumentación de medida: calentamiento, repeticiones, estadísticos, memoria. |
| `suites.py` | Las ocho suites y los 25 benchmarks concretos. |
| `__main__.py` | Ejecución, comparación contra la baseline y código de salida. |
| `baseline.json` | Referencia vigente. Se regenera **conscientemente**, nunca por costumbre. |

Las ocho suites: `startup`, `runtime`, `di`, `capabilities`, `events`, `observability`,
`api-protection`, `http`.

## Cómo se mide, y por qué así

Las decisiones de método están razonadas en los docstrings de `harness.py` (calentamiento,
mediana y p95 en vez de media, memoria como pico de asignación en vez de RSS, GC desactivado
durante la medida) y de `__main__.py` (comparación por mínimo, umbral relativo del 60%, suelo
absoluto de 1 µs, reconfirmación de sospechosos). Todas salen de medir la varianza real de esta
suite en este contenedor, no de números elegidos a ojo; la tabla de dispersión está en
[docs/BENCHMARKS.md](../docs/BENCHMARKS.md).

Sin dependencias nuevas: `time.perf_counter` y `tracemalloc` de la librería estándar. Añadir
`pytest-benchmark` o `asv` exigiría su propio ADR ([CLAUDE.md](../CLAUDE.md) §4) a cambio de una
precisión que no cambiaría ninguna decisión.

## Límites que conviene conocer

En un contenedor compartido esta suite **detecta regresiones de orden de magnitud** — las que
rompen producción — y **no detecta** degradaciones finas del 10-20% en las operaciones dominadas
por asignación de memoria. Para eso haría falta una máquina dedicada. Es una limitación del
entorno, no de la herramienta, y está documentada en vez de disimulada subiendo umbrales hasta
que la puerta nunca falle.

## Cuándo regenerar la baseline

Solo cuando el cambio de rendimiento sea **intencionado y explicado**: una optimización que se
quiere fijar como nuevo suelo, o un cambio funcional aprobado que legítimamente cuesta más.
Regenerarla para silenciar una regresión que nadie ha entendido destruye justo aquello que hace
útil a la suite. La baseline se commitea junto al cambio que la justifica, y ese cambio se
explica en `CHANGELOG.md`.
