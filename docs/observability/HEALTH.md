# Health Checks y Diagnóstico — TEAF

`CompositeHealthChecker`/`HealthCheck`/`HealthReport`/`DiagnosticReport` (`teaf.observability`, Sprint 2.8, ADR-008) — health checks compuestos y diagnóstico agregado del Runtime. Ver [OBSERVABILITY.md](OBSERVABILITY.md) para cómo encaja con el resto de la plataforma.

## 1. El problema que resuelve

Desde el Sprint 2.5, `ModuleBuilder.add_healthcheck(name=..., check=...)` permite a cualquier módulo declarar un `ModuleHealth` — pero, hasta este Sprint, **ningún endpoint lo invocaba** (documentado explícitamente en `sdk/health.py`: "ningún scheduler ni endpoint invoca estas funciones todavía"). `CompositeHealthChecker` (`teaf/_internal/observability/health/checker.py`) cierra esa brecha.

## 2. `CompositeHealthChecker`

```python
class CompositeHealthChecker:
    def __init__(self, checks: Sequence[HealthCheck] = ()) -> None: ...

    @classmethod
    def from_modules(cls, modules: Sequence[ModuleBase]) -> CompositeHealthChecker:
        """Construye el checker a partir de los health_checks declarados por cada módulo."""

    def check_all(self) -> HealthReport:
        """Evalúa cada HealthCheck y agrega el resultado (peor estado crítico gana)."""
```

`from_modules()` recorre `module.get_manifest().health_checks` de cada módulo y construye un `HealthCheck` por cada `ModuleHealth`, con nombre `"{module_id}.{health_name}"` (p. ej. `"security.security.ping"`).

`check_all()`:
- Evalúa cada `check()` — si lanza una excepción, cuenta como `UNHEALTHY` (un módulo que no puede ni reportar su propio estado no es "desconocido", es un fallo real; el `check_all()` nunca propaga la excepción).
- Un `HealthCheck` con `check=None` cuenta como `UNKNOWN`.
- El estado agregado (`HealthReport.overall`) es el peor entre los checks marcados `critical=True` (por defecto) — un check no crítico (`critical=False`) aparece en el desglose pero no degrada el agregado.
- Orden de severidad: `UNHEALTHY` > `DEGRADED` > `UNKNOWN` > `HEALTHY`.

## 3. `/health`/`/ready`/`/live`

`Application` ya conecta `CompositeHealthChecker.from_modules(app.state.bootstrapped_modules)` a estas tres rutas — ninguna aplicación necesita construir el checker a mano:

| Ruta | Semántica | Evalúa dependencias |
|---|---|---|
| `GET /health` | Estado general + desglose por módulo | Sí — `"status": "ok"` si no hay ningún `UNHEALTHY`, `"degraded"` si lo hay |
| `GET /ready` | Readiness probe (Kubernetes/Azure App Service) | Sí — `200` si nada crítico está `UNHEALTHY`, `503` si sí |
| `GET /live` | Liveness probe | **No, a propósito** — solo confirma que el proceso responde |

`/live` nunca evalúa dependencias deliberadamente: si evaluara, una dependencia externa caída degradaría un contenedor sano, provocando reinicios en cascada del orquestador sin ningún beneficio (el proceso seguía vivo, solo una dependencia estaba mal — eso es exactamente lo que `/ready` ya comunica).

Un módulo `DEGRADED` no bloquea el tráfico — `/ready` sigue devolviendo `200` (peor servicio, pero servicio); solo `UNHEALTHY` hace que `/ready` devuelva `503`.

## 4. Runtime Diagnostics — `build_diagnostic_report()`

```python
from teaf.observability import build_diagnostic_report

report = build_diagnostic_report(runtime, bootstrapped_modules, event_bus=runtime.event_bus)
report.as_dict()
# {"generatedAt": "...", "runtime": {...}, "health": {"status": "healthy", "checks": {...}}}
```

`DiagnosticReport` envuelve (no duplica) `RuntimeDiagnostics` (Sprint 2.4, ya expuesta vía `GET /runtime/info`: módulos/servicios/capacidades/plugins/features registrados, grafo de dependencias, estadísticas del `ServiceContainer`, memoria RSS y CPU vía `resource.getrusage()`) y le añade el `HealthReport` agregado — Event Bus, Service Container y módulos cargados ya están cubiertos por los campos existentes de `RuntimeDiagnostics`, sin duplicarlos aquí. Publica `diagnostic.generated` en el `EventBus` si se le pasa uno.

## 5. Ejemplo ejecutable

[`examples/health-checks/`](../../examples/health-checks/) — dos módulos con salud distinta, y cómo `/health`/`/ready` agregan el peor estado.
