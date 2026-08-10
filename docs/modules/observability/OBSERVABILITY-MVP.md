# Observabilidad MVP — Sprint 3.1-light

## Estado en v1.0-beta

TEAF v1.0-beta incluye observabilidad **operacional mínima**: todo lo necesario para investigar problemas en desarrollo y staging, sin dashboards predefinidos (añadidos en v1.0.1).

## Qué Está Incluido

### 1. Trazas Distribuidas
- **Correlation IDs** automáticos por petición HTTP (header `X-Correlation-ID` → `Tracer.start_span()`)
- **Trace context** propagado a través de contexto local (para llamadas sync/async dentro de la app)
- **Span attributes** automáticos: método HTTP, path, status code
- **Exportadores**: OpenTelemetry (OTLP-HTTP, Console, Jaeger, Zipkin, Azure Monitor, etc.)

**Cómo usar**:
```python
from teaf import Application, Observability

app = Application(modules=[
    Observability(exporter="azure-monitor")  # o "console" para dev
])

# Cada petición HTTP automáticamente:
# 1. Genera un trace-id único
# 2. Abre un span SERVER
# 3. Emite un trace.started event
# 4. Cierra el span + emite trace.finished event
```

### 2. Logs Estructurados
- **JSON logging** por defecto (no plain text)
- **Correlation ID + Trace ID + Span ID** automáticos en cada log
- **Niveles**: DEBUG, INFO, WARNING, ERROR (con filtrado por nivel en el middleware)

**Cómo usar**:
```python
from teaf._internal.core.logging import get_logger

logger = get_logger(__name__)

# Automáticamente incluye: timestamp, level, trace_id, span_id, correlation_id
logger.info("user_signed_in", user_id="usr_123", method="JWT")
# JSON: {"timestamp": "...", "level": "INFO", "trace_id": "...", "span_id": "...", "user_id": "usr_123", "method": "JWT"}
```

### 3. Métricas RED (Rate, Errors, Duration)
- **Request Duration**: histograma `http.server.request.duration` (segundos)
- **Request Rate**: implícito en conteos de eventos
- **Error Rate**: codificado en `http.response.status_code` (4xx, 5xx)

**Atributos de métrica automáticos**:
```
http.request.method = GET | POST | PUT | DELETE | ...
url.path = /health | /info | /api/users | ...
http.response.status_code = 200 | 404 | 500 | ...
```

### 4. Health Checks
- Endpoint `/health` (liveness + readiness)
- Endpoint `/ready` (detailed readiness)
- Checks extensibles por módulo

**Uso**:
```bash
curl http://localhost:8000/health
# {"status": "healthy", "checks": {"core": "healthy", "observability": "healthy", ...}}

curl http://localhost:8000/ready
# {"status": "ready", "details": {"observability": {"status": "ready"}}}
```

### 5. Información de Runtime
- Endpoint `/runtime/info` — diagnostics, versión, módulos cargados, capacidades

---

## Qué NO Está Incluido (v1.0.1)

### Dashboards
- No hay Grafana, Azure Monitor dashboards predefinidos
- Adoptor proporciona sus propios dashboards
- Exportadores soportan destinos populares (OTLP, Prometheus, Jaeger, etc.)

### Alertas
- No hay reglas de alerta predefinidas
- Adoptor configura alertas en su plataforma de monitoreo (Grafana, PagerDuty, etc.)

### EventBus Distribuido
- EventBus funciona en memoria (local a cada instancia)
- Multi-instancia comparte trazas vía OTLP, pero eventos no se distribuyen
- Redis Streams distribuido planeado para v1.0.1

---

## Flujo de Debugging Multi-Instancia (MVP)

Escenario: 3 instancias de app, petición viaja A → B → C.

### Hoy (v1.0-beta):
1. **Correlación**:
   - Petición ingresa A: genera `trace_id = "abc123"`, `correlation_id = "req_789"`
   - Header `X-Correlation-ID` propagado a B, C (requiere cliente HTTP que lo re-envía)
   - A emite trace a OTLP → aparece en portal de trazas (Jaeger, Azure, etc.)
   - B emite trace a OTLP → agrupado por `trace_id`
   - C emite trace a OTLP → completa cadena visible en portal

2. **Logs**:
   - Logs de A, B, C enviados a destino centralizado (ELK, splunk, Azure Logs)
   - Buscar por `trace_id = "abc123"` → logs de toda la cadena correlacionados

3. **Limitación**:
   - Si A publica evento interno (EventBus) que B debe recibir, ambos usan memoria local
   - Eventos no se replican: B no recibe evento de A
   - **Workaround**: Usar webhooks o llamadas HTTP directas (no optimal para MVP)

### Mejora (v1.0.1): EventBus distribuido
- A publica a Redis Streams → B se subscribe → C se subscribe
- Eventos distribuidos en toda la cadena
- Ya probado vía feature flag en esta versión

---

## Configuración Mínima

```python
# .env
OBSERVABILITY_EXPORTER=console  # o: azure-monitor, otlp, prometheus, jaeger, etc.
OBSERVABILITY_SAMPLE_RATIO=1.0  # 0.0-1.0, muestreo de trazas
```

```python
# main.py
from teaf import Application, Observability

app = Application(
    modules=[
        Observability(
            exporter=os.getenv("OBSERVABILITY_EXPORTER", "console"),
            sampling_ratio=float(os.getenv("OBSERVABILITY_SAMPLE_RATIO", "1.0")),
        )
    ]
)
```

---

## Ejemplos

### Console (Desarrollo)
```bash
python -c "
from teaf import Application, Observability
import logging

logging.basicConfig(level=logging.INFO)
app = Application(modules=[Observability(exporter='console')])

# Trazas se emiten a stdout:
# trace.started traceId=abc123 spanId=def456
# trace.finished traceId=abc123 spanId=def456 statusCode=200
"
```

### Azure Monitor (Producción)
```python
Observability(
    exporter="azure-monitor",
    otlp_endpoint="https://<workspace>.monitor.azure.com/api/v1/traces",
)
```

### Prometheus + Grafana
```python
Observability(
    exporter="prometheus",
    prometheus_port=8001,  # /metrics en :8001
)

# Grafana scrapes http://localhost:8001/metrics
```

---

## Validación en Tests

```bash
# Verificar trazas distribuidas funcionan
pytest tests/integration/test_observability_module_bootstrap.py -v

# Verificar middleware registra métricas
pytest tests/unit/test_observability_*.py -v

# Verificar logs incluyen trace_id
pytest tests/integration/ -k "log" -v
```

---

## Roadmap v1.0.1+

- **EventBus distribuido** (Redis Streams)
- **Dashboards predefinidos** (Grafana, Azure Monitor)
- **Alertas estándar** (SLO-based)
- **Tracing avanzado** (sampling strategies, probabilistic sampling)
- **Correlación de logs multi-tenant** (si multi-tenancy entra en v1.0)

---

## Limitaciones Documentadas

| Aspecto | Estado | Razón |
|---|---|---|
| EventBus multi-instancia | ❌ No | Memory-only; v1.0.1 con Redis Streams |
| Dashboards predefinidos | ❌ No | Adoptor proporciona; exportadores soportan destinos |
| Alertas automáticas | ❌ No | Configuración en plataforma de monitoreo (Grafana, Azure, etc.) |
| Muestreo de trazas | ⚠️ Parcial | Head-based + tail-based planeado para v1.0.1 |
| Baggage propagation | ❌ No | OpenTelemetry Baggage standard no implementado |

---

## Contacto / Soporte

- Docs completos: [`docs/modules/observability/`](../OBSERVABILITY.md)
- Issues de tracking: [BACKLOG.md](../../roadmap/BACKLOG.md) — sección "Sprint 3.1+"
