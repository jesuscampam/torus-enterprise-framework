# `loadtests/` — pruebas de carga de TEAF

Miden **la aplicación entera bajo peticiones concurrentes sostenidas**: qué rinde, qué se degrada
primero y, sobre todo, si algo falla cuando hay concurrencia real.

Introducidas en Sprint 2.9.1 ([CHANGELOG.md](../CHANGELOG.md)). Los resultados y su lectura viven
en [docs/PERFORMANCE.md](../docs/PERFORMANCE.md); este README describe la herramienta.

## Diferencia con `benchmarks/`

No se solapan, y confundirlas lleva a medir dos veces lo mismo:

| | [`benchmarks/`](../benchmarks/README.md) | `loadtests/` |
|---|---|---|
| Qué mide | Una operación aislada, en serie | La aplicación completa, concurrente |
| Responde a | «¿Cuánto cuesta esto?» | «¿Aguanta, y qué se rompe antes?» |
| ¿Puerta de calidad? | Sí — falla por regresión | Solo falla por **errores**, no por rendimiento |

Un cambio puede dejar los benchmarks intactos y aun así arruinar el comportamiento bajo carga —
un candado global, por ejemplo, solo se nota con concurrencia.

## Uso

```bash
python -m loadtests                                # los nueve escenarios
python -m loadtests --list                         # qué escenarios hay
python -m loadtests --scenario health security     # solo esos
python -m loadtests --requests 5000 --concurrency 64
python -m loadtests --json resultados.json
```

Sale con código distinto de cero **solo si alguna petición falló**. El rendimiento absoluto en un
contenedor compartido no es un umbral defendible, y una puerta que falla por el ruido del
anfitrión acaba desactivada; un 500 bajo concurrencia, en cambio, es un defecto tanto si la
máquina va rápida como si va lenta.

## Escenarios y sus controles

Cada escenario aísla un subsistema, y **solo son válidas las comparaciones por pares**:

| Escenario | Control | La diferencia mide |
|---|---|---|
| `security` | `health` | Middleware de seguridad. |
| `rate-limit` | `health` | Comprobar el límite en cada petición. |
| `rate-limit-rejecting` | `rate-limit` | Rechazar frente a atender. |
| `logging` | `baseline` | Un log estructurado por petición. |
| `tracing` | `baseline` | Un span de OpenTelemetry por petición. |
| `health`, `info`, `runtime` | — | Cifras absolutas de los endpoints de sistema. |

`baseline` es una ruta trivial sobre la misma `Application`. Existe porque sin él `logging` y
`tracing` parecerían más rápidos que `health` — no por ser gratis, sino porque `/health` ejecuta
comprobaciones de salud reales. Comparar contra el control equivocado es la forma más fácil de
sacar una conclusión al revés, y esta suite ya lo hizo una vez antes de corregirse.

## Qué se mide

Throughput (rps), latencia p50/p95/p99/máxima, errores y reparto de códigos de estado, tiempo de
CPU y porcentaje sobre el tiempo de reloj, crecimiento de RSS durante la ejecución y pico de RSS
del proceso.

## Límites que conviene conocer

La aplicación se ejecuta **en proceso** sobre su transporte ASGI, sin servidor HTTP ni sockets: el
objetivo es medir lo que añade TEAF, no uvicorn ni la pila de red del contenedor, que dominarían
el resultado. **Las cifras de rps no son las de un despliegue real** — lo comparable entre
versiones es cuánto de ese coste pone el framework.

Un único proceso Python con un solo bucle de eventos tampoco se beneficia de subir mucho la
concurrencia: por encima de ~32 peticiones en vuelo se mide el encolado del propio bucle.

## Contenido

| Archivo | Responsabilidad |
|---|---|
| `harness.py` | Instrumentación: ciclo de vida ASGI, concurrencia, latencias, CPU y memoria. |
| `scenarios.py` | Los nueve escenarios y sus controles. |
| `__main__.py` | Ejecución, tabla de resultados, volcado JSON y código de salida. |

Sin dependencias nuevas: `httpx` (ya en el stack por `TestClient`), más `asyncio` y `resource` de
la librería estándar. Añadir `locust` o `k6` exigiría su propio ADR ([CLAUDE.md](../CLAUDE.md) §4).
