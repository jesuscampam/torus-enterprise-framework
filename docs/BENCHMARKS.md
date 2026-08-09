# Benchmarks — baseline de v0.10.0-alpha

Baseline oficial de la suite [`benchmarks/`](../benchmarks/README.md), fijada en Sprint 2.9.1 y
**regenerada en Sprint 3.0** — ver [«Por qué se regeneró en Sprint 3.0»](#por-qué-se-regeneró-en-sprint-30).
Sirve para dos cosas: dar una cifra a «¿cuánto cuesta esto?» y hacer fallar la puerta de calidad
cuando una versión posterior lo empeore.

La herramienta y su método están en [`benchmarks/README.md`](../benchmarks/README.md); las cifras y
su lectura, aquí. Las pruebas bajo concurrencia son otra cosa distinta y viven en
[PERFORMANCE.md](PERFORMANCE.md).

**Entorno de la medida**: CPython 3.11.15, Linux x86_64, contenedor compartido. Dos ejecuciones
solo son comparables si coinciden en estos cuatro datos — se guardan dentro de
`benchmarks/baseline.json` justamente por eso.

## Cómo leer la tabla

Muchas operaciones cuestan menos de un microsegundo, y medir una sola vez a esa escala mide el
reloj, no la operación. Por eso se miden **en lotes** y la columna «coste unitario» divide entre el
tamaño del lote. La columna «mediana» es lo que devuelve la herramienta; la de «mínimo» es la que
usa la comparación contra baseline (ver más abajo).

## Arranque

| Benchmark | Mediana | Mínimo | Memoria pico | v0.9.1-alpha (mínimo) |
|---|---:|---:|---:|---:|
| `Application()` (construcción) | 1.85 ms | 1.73 ms | 129.7 KiB | 2.77 ms |
| Arranque ASGI completo (construcción + startup + shutdown) | 4.10 ms | 3.80 ms | 171.7 KiB | 5.63 ms |
| Bootstrap de un módulo (`Application(modules=[...])` + ciclo completo) | 4.12 ms | 3.91 ms | 173.8 KiB | 6.03 ms |

Estas tres son las cifras que más se notan en desarrollo: las paga cada arranque del servidor y
cada prueba que construye una aplicación. **Sprint 2.9.1 las redujo entre 2.9× y 5.5×** — el
detalle de cómo está en [PERFORMANCE.md](PERFORMANCE.md). **Sprint 3.0 las vuelve a reducir entre
un 33 % y un 38 %**, y la memoria de construcción un 32 % (192.1 → 129.7 KiB), sin que el sprint
tocase el camino de arranque.

### Por qué se regeneró en Sprint 3.0

La desviación es de **mejora**, no de regresión, y tiene una causa única y comprobable: el salto de
`starlette` 0.41.3 a **1.4.1** (vía `fastapi` 0.141.1). Es la única variable que cambia en el
camino de construcción de una `Application` — Sprint 3.0 no tocó el arranque, y las piezas nuevas
(caché, proxies de confianza) **no se construyen si no se configuran**, que es justo lo que estas
cifras confirman: si el módulo de caché costase algo sin configurar, aparecería aquí.

Se regenera la baseline en vez de conservar la antigua porque una baseline holgada deja de
detectar: con las cifras de 2.9.1, una regresión futura que devolviera el arranque a 2.77 ms
pasaría inadvertida. Fijar las nuevas mantiene la puerta tan estricta como antes respecto al
estado real del framework.

Ningún benchmark empeoró. La suite completa se ejecutó dos veces con el mismo resultado antes de
regenerar.

## Runtime y módulos

| Benchmark | Mediana | Coste unitario |
|---|---:|---:|
| `Runtime.describe()` | 4.15 µs | 4.15 µs |
| `Runtime.diagnostics()` | 11.03 µs | 11.03 µs |

## Inyección de dependencias

| Benchmark | Mediana (lote 1.000) | Coste unitario |
|---|---:|---:|
| `resolve()` SINGLETON | 359 µs | **0.36 µs** |
| `resolve()` SCOPED | 499 µs | **0.50 µs** |
| `resolve()` TRANSIENT | 704 µs | **0.70 µs** |
| `register()` de un servicio | 0.77 µs | 0.77 µs |

El orden es el esperado y merece leerse: un singleton es una búsqueda en diccionario; un scoped
añade la resolución del ámbito; un transient construye una instancia nueva cada vez. Resolver un
servicio cuesta **menos de un microsegundo** en los tres casos, así que la inyección de
dependencias no es un factor en el coste de una petición.

## Capacidades

| Benchmark | Mediana (lote 1.000) | Coste unitario |
|---|---:|---:|
| Búsqueda de capacidad | 113 µs | **0.11 µs** |
| Listado de capacidades | 0.36 µs | 0.36 µs |

## Event Bus

| Benchmark | Mediana (lote 1.000) | Coste unitario |
|---|---:|---:|
| `publish()` sin suscriptores | 159 µs | **0.16 µs** |
| `publish()` con 1 suscriptor | 205 µs | **0.20 µs** |
| `subscribe()` + `unsubscribe()` | 267 µs | 0.27 µs |

Publicar sin suscriptores cuesta 0.16 µs: emitir eventos que nadie escucha es efectivamente
gratis, que es la propiedad que permite instrumentar el framework sin condicionar cada llamada.

## Observabilidad

| Benchmark | Mediana | Coste unitario |
|---|---:|---:|
| Abrir y cerrar un span (lote 100) | 2.90 ms | **29.0 µs** |
| `Counter.add()` (lote 1.000) | 2.17 ms | **2.17 µs** |
| `Histogram.record()` (lote 1.000) | 2.23 ms | **2.23 µs** |
| Log estructurado filtrado (lote 100) | 30.7 µs | **0.31 µs** |

Un span cuesta ~29 µs, dos órdenes de magnitud más que una métrica. No es un defecto de TEAF —es
el coste del SDK de OpenTelemetry— pero sí la razón por la que el muestreo (`sampling_ratio`)
existe y por la que conviene usarlo en rutas de alto tráfico.

Un log **por debajo del nivel activo** cuesta 0.31 µs: el filtrado ocurre antes de formatear, así
que dejar `logger.debug(...)` en caliente no penaliza producción.

## Protección de APIs

| Benchmark | Mediana | Coste unitario |
|---|---:|---:|
| `RateLimiter.acquire()` (lote 1.000, ventana fija) | 10.54 ms | **10.5 µs** |
| `RequestValidator.validate_request()` (lote 1.000) | 1.94 ms | **1.94 µs** |
| `CorsPolicy.response_headers()` (lote 1.000) | 1.77 ms | **1.77 µs** |
| `ApiAudit.record()` (lote 1.000) | 1.06 ms | **1.06 µs** |
| Compresión GZip (lote 100, respuestas de 4.434 B) | 2.33 ms | **23.3 µs** |

## Cadena HTTP completa

| Benchmark | Mediana |
|---|---:|
| FastAPI sin protección | 3.26 ms |
| FastAPI con 4 middlewares (rate limiting + CORS + validación + auditoría) | 5.26 ms |

Las cuatro capas de protección añaden ~2.0 ms sobre una petición de 3.3 ms. Es la cifra que hay
que tener delante al decidir cuáles activar: no son gratis, y la suma de los costes unitarios de
arriba (≈15 µs) no las explica — la mayor parte es el sobrecoste de encadenar middlewares de
Starlette, cada uno de los cuales envuelve la petición en otra capa de `async`.

## Regresiones: cómo se decide que algo empeoró

Tres reglas, y ninguna es arbitraria — salen de ejecutar la suite tres veces seguidas **sin tocar
el código** y medir cuánto se movía sola:

| Regla | Valor | Por qué |
|---|---|---|
| Estadístico comparado | **mínimo**, no mediana | El ruido es unilateral: puede hacer que algo tarde más, nunca menos. Bajó la dispersión del peor caso del 88% al 41%. |
| Umbral relativo | **60%** | La dispersión en reposo llega al 52% en los benchmarks dominados por asignación de memoria. |
| Suelo absoluto | **1 µs** | `register()` oscila un 41% en reposo, pero solo 0.29 µs. Sin suelo, el ruido de lo más rápido dispara la puerta. |

Además, **una regresión detectada se vuelve a medir antes de reportarse**. Durante este mismo
Sprint, «Arranque ASGI completo» dio 13.3 ms en una ejecución y 5.2 ms en las tres siguientes, sin
cambio alguno de código: un pico del anfitrión. Volver a medir solo las suites sospechosas
distingue eso de una regresión real —que por definición se reproduce— y cuesta en proporción al
problema.

### Dispersión medida (tres ejecuciones idénticas)

Es la tabla que justifica los umbrales de arriba, y también el mapa de en qué cifras conviene
confiar:

| Benchmark | Dispersión mediana | Dispersión mínimo |
|---|---:|---:|
| `register()` de un servicio | 88% | 41% |
| Compresión GZip | 58% | 52% |
| FastAPI sin protección | 32% | 21% |
| Bootstrap de un módulo | 21% | 32% |
| Abrir y cerrar un span | 20% | 9% |
| `resolve()` TRANSIENT | 15% | 11% |
| Arranque ASGI completo | 12% | 20% |
| *(los otros 18)* | ≤ 9% | ≤ 5% |

## Límite que esto impone

Conviene decirlo sin adornos: en un contenedor compartido esta suite **detecta regresiones de orden
de magnitud** —las que rompen producción— y **no detecta** degradaciones finas del 10-20% en las
operaciones pesadas. Para eso haría falta una máquina dedicada. La alternativa era subir los
umbrales hasta que la puerta no fallara nunca, que es peor: una puerta que no puede fallar no
informa de nada.

## Un episodio del Sprint 3.0.3 que conviene recordar

Durante la validación de v0.10.3-alpha, la puerta falló con seis mediciones entre **+64 % y +80 %**
sobre esta baseline: `resolve()` en sus tres *lifetimes*, `publish()` con un suscriptor,
`subscribe()` + `unsubscribe()`, búsqueda de capacidad y compresión GZip.

La hipótesis fácil era culpar al cambio del sprint (subir `pydantic`, `asyncpg` y `sqlalchemy`). Se
descartó con un experimento controlado: los mismos benchmarks, en la misma máquina y en la misma
sesión, con el **pin anterior `pydantic==2.10.4`**, daban la misma degradación — GZip midió
2048.70 µs con 2.10.4 y 2048.12 µs con 2.12.0, el mismo número. Además lo degradado incluía
compresión GZip y resolución del contenedor de DI, que no tocan `pydantic` por ningún camino.
Diagnóstico: **el anfitrión, momentáneamente más lento**, exactamente el límite que advierte la
sección anterior.

**La baseline no se regeneró.** Horas después, sin tocar ni un número de `baseline.json`, la puerta
volvió sola a verde — y en el **3.0 Final Hardening**, poco después, volvió a rojo con las mismas
siete mediciones y el mismo orden de magnitud (GZip: 1242 µs de baseline frente a 2048 µs, 2048 µs y
2033 µs en tres sesiones distintas, con dos juegos de dependencias distintos). No se recuperó:
**oscila**.

Eso es exactamente lo que hace útil no haberla reescrito. Si se hubiera regenerado durante
cualquiera de los picos, la baseline habría quedado inflada un 70 % de forma permanente y habría
dejado de detectar regresiones reales para siempre. El criterio operativo mientras la suite viva en
un contenedor compartido: **un rojo uniforme (+60 % o más) repartido por operaciones que no
comparten código —resolución de DI, EventBus y compresión GZip a la vez— es el anfitrión, no una
regresión.** Una regresión real aparece concentrada donde se tocó el código.

## Regenerar la baseline

```bash
python -m benchmarks --save-baseline
```

Solo cuando el cambio de rendimiento sea **intencionado y explicado**. Regenerarla para silenciar
una regresión que nadie ha entendido destruye justo aquello que la hace útil. Se commitea junto al
cambio que la justifica, y ese cambio se explica en [CHANGELOG.md](../CHANGELOG.md).
