# Rendimiento — v0.9.1-alpha

Qué se optimizó en Sprint 2.9.1, cuánto se ganó y qué se midió bajo carga. Las cifras aisladas por
operación están en [BENCHMARKS.md](BENCHMARKS.md); aquí están las mejoras y el comportamiento
concurrente.

## Resumen: lo que cambió en v0.9.1-alpha

| Métrica | v0.9.0-alpha | v0.9.1-alpha | Mejora |
|---|---:|---:|---:|
| `Application()` (construcción) | 15.50 ms | **2.82 ms** | **5.5×** |
| Arranque ASGI completo | 18.42 ms | **5.79 ms** | **3.2×** |
| Bootstrap de un módulo | 17.96 ms | **6.25 ms** | **2.9×** |
| Memoria de construcción | 290.7 KiB | **192.1 KiB** | **−34%** |

Ninguna respuesta cambió un solo byte. Las tres optimizaciones están abajo, con el porqué.

## 1. Modelos de respuesta: el 97% del arranque

**El hallazgo.** Perfilar `Application()` mostró que **el 97% de sus 15.5 ms** no era TEAF: era
FastAPI generando, ruta por ruta, el modelo Pydantic de respuesta de sus 30 endpoints de sistema.
Trabajo que se paga íntegro en cada arranque —y en cada prueba que construye una aplicación— para
validar respuestas que el propio framework produce y ya sabe correctas.

**El cambio.** Declarar `response_model=None` en las 15 rutas de sistema
(`runtime/api.py`, `monitoring/health.py`, `monitoring/info.py`), que le dice a FastAPI que no
construya el `TypeAdapter`.

**El problema que eso creaba, y por qué no se aceptó.** Medido en aislado, `response_model=None` es
9× más rápido y devuelve **respuestas byte a byte idénticas**. Pero degradaba el esquema OpenAPI:
lo que era `{"type": "object"}` pasaba a ser `{}`. Un cliente que genere código desde el esquema
pierde información real. Cambiar rendimiento por contrato no es una optimización, es una rebaja.

**La solución.** Constantes explícitas de `responses=` en
[`teaf/_internal/shared/openapi.py`](../teaf/_internal/shared/openapi.py) que reponen el esquema a
mano. Se conserva todo salvo el `title` autogenerado, que no lo consume nadie.

**Blindaje.** 33 pruebas en `tests/unit/test_openapi_responses.py` verifican a la vez el esquema
publicado y que los cuerpos siguen siendo idénticos. Sin ellas, un Sprint futuro que añada una
ruta sin `responses=` reintroduciría la degradación en silencio.

## 2. Fuga de memoria en los almacenes en memoria

**El hallazgo.** Los tres almacenes de `teaf/_internal/api/providers/memory.py`
(rate limiting, cuotas, idempotencia) solo caducaban entradas **de forma perezosa**: al consultar
una clave concreta. Una clave que nunca se vuelve a consultar no se libera nunca.

**Por qué era grave.** El crecimiento no depende del volumen de tráfico sino de su
**cardinalidad** —IPs distintas, claves de idempotencia distintas, tenants distintos— que es
justo lo que un atacante controla. Un proceso de larga vida crecía sin techo.

**El cambio.** Purga amortizada: cada 512 escrituras (`_PURGE_INTERVAL_WRITES`) se recorre el
almacén una vez y se eliminan las entradas caducadas. Amortizado, el coste por escritura es
constante y despreciable; el techo pasa a depender de la ventana de caducidad, no del tiempo.

**Verificación empírica** (`tests/unit/test_memory_bounds.py`): tras 1.536 escrituras con claves
distintas y ventana vencida, **1.536 → 10 entradas retenidas (−99,3%)**. Las pruebas se
comprobaron contra el código sin arreglar: fallan, que es lo que las hace valer.

## 3. Código muerto

Eliminados 7 módulos sin ningún uso: `shared/{collections,dates,strings,validation}.py` y
`providers/telemetry/{logger,metrics,tracer}_provider.py`. Estos últimos los declaraba muertos
[ADR-008](architecture/adr/ADR-008-enterprise-observability.md) —«todos abstractos, ninguno
instanciado en ningún sitio»— y además colisionaban por nombre con el `TracerProvider` real de
OpenTelemetry, que es una confusión cara de pagar cuando alguien lee el import equivocado.

Efecto lateral: `mypy --strict` pasó de 28 errores a **0 sobre 225 ficheros**. La mayoría de esos
28 eran artefactos de invocar `mypy` en vez de `python -m mypy` —el ejecutable suelto no resolvía
los tipos de FastAPI/Starlette y los degradaba a `Any`, ocultando errores reales, entre ellos un
`otel_metrics.Gauge` que no existe—. La puerta de calidad fija ahora la invocación correcta.

## Comportamiento bajo carga

Medido con [`loadtests/`](../loadtests/README.md): 2.000 peticiones por escenario, 32 en vuelo,
sobre el transporte ASGI en proceso.

| Escenario | RPS | p50 | p95 | p99 | CPU | Errores |
|---|---:|---:|---:|---:|---:|---:|
| `health` | 623 | 41.6 ms | 107 ms | 117 ms | 105% | **0** |
| `info` | 558 | 46.0 ms | 119 ms | 143 ms | 105% | **0** |
| `runtime` | 536 | 49.6 ms | 116 ms | 135 ms | 105% | **0** |
| `security` | 438 | 59.0 ms | 145 ms | 167 ms | 104% | **0** |
| `baseline` (ruta trivial) | 807 | 24.6 ms | 101 ms | 106 ms | 100% | **0** |
| `logging` | 820 | 24.3 ms | 96 ms | 105 ms | 100% | **0** |
| `tracing` | 747 | 27.0 ms | 101 ms | 107 ms | 100% | **0** |
| `rate-limit` | 428 | 61.3 ms | 146 ms | 160 ms | 103% | **0** |
| `rate-limit-rejecting` | 1.597 | 9.1 ms | 14 ms | 91 ms | 100% | **0** |

**Cero errores en los nueve escenarios**, que es el resultado que de verdad importa: ninguna ruta
degenera en 500 bajo concurrencia.

### Lo que cuesta cada capa

Solo son válidas las comparaciones contra el control de cada escenario (ver
[`loadtests/README.md`](../loadtests/README.md)):

| Capa | Comparación | Coste |
|---|---|---:|
| Middleware de seguridad | `security` vs `health` | **−30%** de throughput |
| Comprobar el límite | `rate-limit` vs `health` | **−31%** |
| Un span por petición | `tracing` vs `baseline` | **−7%** |
| Un log estructurado por petición | `logging` vs `baseline` | **≈0%** (dentro del ruido) |

**Rechazar es 3,7× más barato que atender** (1.597 vs 428 rps). Es la propiedad que hay que
exigirle a un limitador: si rechazar costara más que servir, un atacante lo usaría como
amplificador en lugar de chocar contra él.

El logging estructurado no se distingue del control. Tiene sentido: el filtrado por nivel ocurre
antes de formatear nada.

### Cómo leer los RPS

**No son las cifras de un despliegue real.** La aplicación se ejecuta en proceso sobre su
transporte ASGI, sin servidor HTTP ni sockets, precisamente para medir lo que añade TEAF y no lo
que añaden uvicorn y la pila de red del contenedor. Lo comparable entre versiones es el coste
relativo de cada capa; el número absoluto no lo es.

La CPU al 100-105% con 32 peticiones en vuelo confirma además lo esperado: un solo bucle de
eventos satura un núcleo, y la escala horizontal es por procesos, no por concurrencia dentro del
proceso.

## Reproducir

```bash
python -m benchmarks     # operaciones aisladas, compara contra la baseline
python -m loadtests      # concurrencia, falla si hay errores
```
