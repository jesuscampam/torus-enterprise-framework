"""Instrumentación de las pruebas de carga de TEAF (Sprint 2.9.1).

Diferencia con [`benchmarks/`](../benchmarks/README.md), que es lo primero
que hay que tener claro para no duplicar esfuerzo: los benchmarks miden
**una operación aislada** repetida en serie, y responden a «¿cuánto cuesta
esto?». Las pruebas de carga miden **la aplicación entera bajo peticiones
concurrentes sostenidas**, y responden a «¿aguanta, y qué se degrada
primero?». Un cambio puede dejar intactos los benchmarks y aun así arruinar
el comportamiento bajo carga — por ejemplo, un candado global que solo se
nota cuando hay concurrencia real.

Se ejecuta la aplicación **en proceso** sobre su transporte ASGI, sin
servidor HTTP ni sockets. Es deliberado: el objetivo es medir el coste que
añade TEAF, no el de uvicorn ni el de la pila de red del contenedor, que
dominarían el resultado y variarían con el anfitrión. La cifra de
rendimiento absoluto que sale de aquí, por tanto, **no** es la de un
despliegue real; lo que sí es comparable entre versiones es cuánto de ese
coste pone el framework.

Sin dependencias nuevas: ``httpx`` (ya en el stack por ``TestClient``),
``asyncio`` y ``resource`` de la librería estándar.
"""

from __future__ import annotations

import asyncio
import resource
import statistics
import time
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx

#: Peticiones totales por escenario. Suficiente para que las colas se llenen
#: y el coste de arranque quede amortizado, sin que la suite completa pase
#: de unos minutos.
DEFAULT_REQUESTS = 2_000

#: Peticiones en vuelo simultáneas. Un solo proceso Python con un único
#: bucle de eventos no se beneficia de subir mucho más: a partir de aquí se
#: mide el encolado del propio bucle, no el framework.
DEFAULT_CONCURRENCY = 32

#: Peticiones descartadas al principio de cada escenario. La primera de
#: todas paga imports perezosos, cachés vacías y compilación de rutas.
DEFAULT_WARMUP = 50


@dataclass(frozen=True, slots=True)
class LoadScenario:
    """Un escenario: qué aplicación se levanta y qué petición se le lanza."""

    name: str
    description: str
    #: Construye la aplicación ASGI. Es una fábrica, no una instancia, para
    #: que cada escenario arranque limpio y no herede estado del anterior.
    build: Callable[[], Any]
    path: str
    method: str = "GET"
    headers: Mapping[str, str] = field(default_factory=dict)
    expected_status: int = 200


@dataclass(frozen=True, slots=True)
class LoadResult:
    """Resultado de un escenario. Tiempos en milisegundos, memoria en KiB."""

    name: str
    description: str
    requests: int
    concurrency: int
    duration_seconds: float
    throughput_rps: float
    p50_ms: float
    p95_ms: float
    p99_ms: float
    max_ms: float
    errors: int
    status_counts: dict[int, int]
    cpu_seconds: float
    cpu_percent: float
    rss_growth_kib: int
    peak_rss_kib: int

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "requests": self.requests,
            "concurrency": self.concurrency,
            "durationSeconds": round(self.duration_seconds, 3),
            "throughputRps": round(self.throughput_rps, 1),
            "p50Ms": round(self.p50_ms, 3),
            "p95Ms": round(self.p95_ms, 3),
            "p99Ms": round(self.p99_ms, 3),
            "maxMs": round(self.max_ms, 3),
            "errors": self.errors,
            "statusCounts": {
                str(code): count for code, count in sorted(self.status_counts.items())
            },
            "cpuSeconds": round(self.cpu_seconds, 3),
            "cpuPercent": round(self.cpu_percent, 1),
            "rssGrowthKib": self.rss_growth_kib,
            "peakRssKib": self.peak_rss_kib,
        }


@asynccontextmanager
async def run_lifespan(app: Any) -> AsyncIterator[None]:
    """Arranca y para el ciclo de vida ASGI de ``app``.

    ``httpx.ASGITransport`` no ejecuta el ``lifespan`` — solo enruta
    peticiones — y sin él los módulos de TEAF nunca arrancan: se estaría
    midiendo una aplicación a medio construir. Se habla el protocolo
    directamente en lugar de añadir ``asgi-lifespan`` al stack, que
    requeriría su propio ADR ([CLAUDE.md](../CLAUDE.md) §4) para veinte
    líneas.
    """
    to_app: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    from_app: asyncio.Queue[dict[str, str]] = asyncio.Queue()
    scope = {"type": "lifespan", "asgi": {"version": "3.0", "spec_version": "2.0"}}
    task = asyncio.create_task(app(scope, to_app.get, from_app.put))

    await to_app.put({"type": "lifespan.startup"})
    message = await from_app.get()
    if message["type"] == "lifespan.startup.failed":
        task.cancel()
        raise RuntimeError(f"El arranque falló: {message.get('message', '')}")

    try:
        yield
    finally:
        await to_app.put({"type": "lifespan.shutdown"})
        await from_app.get()
        await task


def _current_rss_kib() -> int:
    """RSS actual del proceso en KiB, o 0 si el sistema no lo expone."""
    try:
        with open("/proc/self/status", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        pass
    return 0


def _percentile(ordered: list[float], fraction: float) -> float:
    if not ordered:
        return 0.0
    return ordered[min(int(len(ordered) * fraction), len(ordered) - 1)]


async def run_scenario(
    scenario: LoadScenario,
    *,
    requests: int = DEFAULT_REQUESTS,
    concurrency: int = DEFAULT_CONCURRENCY,
    warmup: int = DEFAULT_WARMUP,
) -> LoadResult:
    """Ejecuta un escenario y devuelve sus métricas.

    Un error no aborta la prueba: se cuenta y se sigue. Una prueba de carga
    que se detiene en el primer fallo no mide nada — la pregunta que
    responde es precisamente *cuántos* fallan y bajo qué carga.
    """
    app = scenario.build()
    latencies: list[float] = []
    status_counts: dict[int, int] = {}
    errors = 0

    async with run_lifespan(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://loadtest") as client:
            for _ in range(warmup):
                try:
                    await client.request(
                        scenario.method, scenario.path, headers=dict(scenario.headers)
                    )
                except Exception:  # noqa: BLE001 — el calentamiento no se mide ni se reporta
                    pass

            semaphore = asyncio.Semaphore(concurrency)

            async def one_request() -> None:
                nonlocal errors
                async with semaphore:
                    started = time.perf_counter()
                    try:
                        response = await client.request(
                            scenario.method, scenario.path, headers=dict(scenario.headers)
                        )
                    except (
                        Exception
                    ):  # noqa: BLE001 — un fallo es un dato, no una excepción a propagar
                        errors += 1
                        return
                    finally:
                        latencies.append((time.perf_counter() - started) * 1000)
                    status_counts[response.status_code] = (
                        status_counts.get(response.status_code, 0) + 1
                    )
                    if response.status_code != scenario.expected_status:
                        errors += 1

            rss_before = _current_rss_kib()
            usage_before = resource.getrusage(resource.RUSAGE_SELF)
            wall_started = time.perf_counter()

            await asyncio.gather(*(one_request() for _ in range(requests)))

            duration = time.perf_counter() - wall_started
            usage_after = resource.getrusage(resource.RUSAGE_SELF)
            rss_after = _current_rss_kib()

    cpu_seconds = (usage_after.ru_utime - usage_before.ru_utime) + (
        usage_after.ru_stime - usage_before.ru_stime
    )
    ordered = sorted(latencies)
    return LoadResult(
        name=scenario.name,
        description=scenario.description,
        requests=requests,
        concurrency=concurrency,
        duration_seconds=duration,
        throughput_rps=requests / duration if duration > 0 else 0.0,
        p50_ms=statistics.median(ordered) if ordered else 0.0,
        p95_ms=_percentile(ordered, 0.95),
        p99_ms=_percentile(ordered, 0.99),
        max_ms=ordered[-1] if ordered else 0.0,
        errors=errors,
        status_counts=status_counts,
        cpu_seconds=cpu_seconds,
        cpu_percent=(cpu_seconds / duration * 100) if duration > 0 else 0.0,
        rss_growth_kib=max(rss_after - rss_before, 0),
        peak_rss_kib=usage_after.ru_maxrss,
    )


def format_table(results: list[LoadResult]) -> str:
    """Tabla de texto alineada con las métricas de cada escenario."""
    if not results:
        return "(sin resultados)"

    width = max(len(result.name) for result in results) + 2
    header = (
        f"{'ESCENARIO':<{width}}{'RPS':>10}{'p50':>9}{'p95':>9}{'p99':>9}"
        f"{'MÁX':>9}{'CPU%':>8}{'RSS+':>10}{'ERR':>6}"
    )
    lines = [header, "─" * len(header)]
    for result in results:
        lines.append(
            f"{result.name:<{width}}"
            f"{result.throughput_rps:>10,.0f}"
            f"{result.p50_ms:>8.2f}m"
            f"{result.p95_ms:>8.2f}m"
            f"{result.p99_ms:>8.2f}m"
            f"{result.max_ms:>8.2f}m"
            f"{result.cpu_percent:>8.0f}"
            f"{result.rss_growth_kib:>9,d}K"
            f"{result.errors:>6,d}"
        )
    return "\n".join(lines)
