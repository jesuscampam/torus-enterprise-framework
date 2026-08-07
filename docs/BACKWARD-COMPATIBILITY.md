# Compatibilidad hacia atrás — v0.9.1-alpha

Qué garantiza TEAF a quien lo consume, cómo se verifica esa garantía de forma mecánica, y el
resultado de aplicarla a v0.9.1-alpha.

Complementa [VERSIONING.md](public-api/VERSIONING.md) (política de versiones) y
[MIGRATION-GUIDE.md](public-api/MIGRATION-GUIDE.md) (cómo migrar entre versiones).

## Qué está cubierto

La garantía alcanza **exclusivamente** a lo que se importa desde `teaf.*`: los 192 símbolos de
`teaf/__init__.py` y de las fachadas por área (`teaf.api`, `teaf.security`, `teaf.observability`,
`teaf.runtime`, ...). Para cada uno se garantiza que no desaparece, no se renombra, y no cambia de
firma de forma incompatible.

**Nada bajo `teaf._internal` está cubierto** — es implementación, así se llama y así se documenta
([ADR-006](architecture/adr/ADR-006-internal-namespace-refactor.md)). Que una aplicación consuma
`teaf._internal` es un defecto de esa aplicación, y la puerta `boundary` existe para detectarlo
antes de que se convierta en costumbre.

## Cómo se verifica

No por revisión humana. [`scripts/check_public_api_surface.py`](../scripts/check_public_api_surface.py)
captura la superficie completa —módulos, clases, funciones, métodos y **firmas**, no solo
nombres— en [`docs/public-api/api-surface.json`](public-api/api-surface.json) y compara la actual
contra esa referencia.

Comparar firmas y no solo nombres es lo que hace útil al comprobador: renombrar un parámetro
posicional, hacer obligatorio uno opcional o reordenar dos argumentos rompe a los consumidores sin
que ningún nombre desaparezca. Un `grep` de símbolos no lo vería.

Distingue además **rupturas** de **ampliaciones**: añadir un método o un parámetro con valor por
defecto no rompe a nadie y no debe hacer fallar la puerta, pero sí debe quedar registrado.

Se ejecuta como la puerta `public-api` dentro de `python scripts/quality_gates.py`.

## Resultado en v0.9.1-alpha

**Compatible al 100%.** Verificado de forma mecánica, no por inspección: se capturó la superficie
de v0.9.0-alpha —guardando los cambios de este Sprint y volviendo al commit anterior— y se comparó
contra la de v0.9.1-alpha.

| Comprobación | Resultado |
|---|---|
| Símbolos públicos | 192 → 192 |
| Símbolos eliminados | **0** |
| Símbolos renombrados | **0** |
| Firmas modificadas de forma incompatible | **0** |
| Ampliaciones (no rompen) | 2 |

Las dos ampliaciones son métodos nuevos, ambos derivados de la corrección de la fuga de memoria
(ver [PERFORMANCE.md](PERFORMANCE.md)):

- `teaf.InMemoryIdempotencyStore.purge_expired`
- `teaf.InMemoryQuotaStore.purge_expired`

Ningún consumidor de v0.9.0-alpha necesita cambiar una sola línea.

## Qué se eliminó, y por qué no cuenta

Sprint 2.9.1 borró 7 módulos de código muerto. Ninguno era alcanzable desde `teaf.*`:

- `teaf/_internal/shared/{collections,dates,strings,validation}.py`
- `teaf/_internal/providers/telemetry/{logger,metrics,tracer}_provider.py`

Los segundos ya los declaraba muertos
[ADR-008](architecture/adr/ADR-008-enterprise-observability.md) («todos abstractos, ninguno
instanciado en ningún sitio»). Que su eliminación no moviera el contador de 192 símbolos es
precisamente la evidencia de que el límite público estaba bien puesto.

## Qué cambió sin romper nada

Cambios internos, invisibles desde fuera salvo por ir más rápido:

| Cambio | Efecto observable |
|---|---|
| `response_model=None` + `responses=` explícitas | Ninguno. Cuerpos byte a byte idénticos, esquema OpenAPI preservado. |
| Purga amortizada en los almacenes en memoria | Ninguno en la API. La memoria deja de crecer sin techo. |
| `app: object` → `app: ASGIApp` en 11 middlewares | Ninguno en tiempo de ejecución — solo tipado más estricto. |
| Eliminación de código muerto | Ninguno. Nada era alcanzable públicamente. |

## Cómo actualizar la referencia

```bash
python scripts/check_public_api_surface.py --update
```

Solo cuando la ampliación de la superficie sea **deliberada y aprobada**. La referencia se
commitea junto al cambio que la justifica. Actualizarla para silenciar una ruptura convierte la
puerta en decoración: si el comprobador señala una ruptura real, lo que hay que arreglar es el
código, no el fichero de referencia.

## Qué no cubre esta garantía

Ser explícito aquí evita discusiones más tarde:

- **Comportamiento no documentado.** Si un consumidor depende de un detalle que ningún documento
  promete —el orden de una lista sin orden garantizado, la redacción exacta de un mensaje de
  error— puede cambiar.
- **Rendimiento.** Ninguna versión garantiza que una operación siga costando lo mismo. Lo que sí
  hay es una baseline y una puerta que avisa ([BENCHMARKS.md](BENCHMARKS.md)).
- **Las versiones `-alpha` entre sí.** Mientras TEAF esté en `0.x`, la política de
  [VERSIONING.md](public-api/VERSIONING.md) permite romper en un cambio de versión menor **si se
  documenta y se justifica**. La compatibilidad total de v0.9.1-alpha es un compromiso de este
  Sprint —era un Sprint de endurecimiento, romper habría sido contradictorio—, no una promesa
  automática de todos los futuros.
