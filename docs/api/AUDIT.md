# Auditoría de API — TEAF

Registro de cada petición servida (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

## 1. Qué se registra

Un `ApiAuditRecord` por petición, con todos los campos exigidos por el Sprint 2.9:

| Campo | Qué contiene |
|---|---|
| `method` / `path` | Verbo y ruta. |
| `statusCode` | Código HTTP de la respuesta. |
| `latencySeconds` | Duración medida de extremo a extremo. |
| `outcome` | `accepted` · `rejected` · `failed` · `replayed`. |
| `identityId` | `principal_id` del `SecurityContext`. |
| `tenantId` | Tenant resuelto. |
| `apiKeyId` | Identificador de la API Key, si la autenticación fue por clave. |
| `clientIp` | IP del cliente (respetando las cabeceras de proxy, si se confía en ellas). |
| `correlationId` | Correlation-id de la petición. |
| `traceId` / `spanId` | Traza activa (Sprint 2.8). |
| `apiVersion` | Versión negociada. |
| `requestBytes` / `responseBytes` | Tamaños. |
| `reason` | Motivo del rechazo o clase de la excepción, cuando aplica. |
| `recordedAt` | Marca de tiempo UTC en ISO 8601. |

## 2. Los cuatro desenlaces

`ApiOutcome` distingue qué pasó realmente, más allá del código HTTP:

| Desenlace | Cuándo |
|---|---|
| `accepted` | Respuesta correcta (`< 400`). |
| `rejected` | El cliente fue rechazado (`4xx`) — por límite, cuota, validación, versión o CORS. |
| `failed` | Fallo del servidor (`5xx`) o excepción no controlada. |
| `replayed` | Se reprodujo una respuesta [idempotente](IDEMPOTENCY.md). |

## 3. Se auditan también los rechazos y los fallos

`ApiAuditMiddleware` se coloca casi en el exterior de la cadena (solo CORS queda por fuera) precisamente para ver **todo**: lo aceptado, lo rechazado por las capas siguientes, y lo que terminó en excepción. Una auditoría que solo viera el tráfico aceptado sería inútil para lo que más importa auditar.

Una excepción no controlada se audita y **se re-lanza intacta**, para que el manejador central produzca la respuesta `500` de siempre.

## 4. Integración con Observability

Tres vías complementarias, ninguna sustituye a las otras:

- **Trazas**: cada registro lleva `traceId`/`spanId`, así que desde una entrada de auditoría se salta a la traza completa de esa petición, sin necesitar ninguna correlación externa.
- **Métricas**: con un `Meter` ([OBSERVABILITY.md](../observability/OBSERVABILITY.md)), `ApiAudit` mantiene un contador `api.audit.records` y un histograma `api.audit.latency`, con las mismas dimensiones que la auditoría.
- **Eventos**: publica `audit.recorded` en el `EventBus` del Runtime, para que cualquier módulo reaccione sin acoplarse a este.

```python
from teaf.api import ApiAudit, InMemoryAuditSink, LoggingAuditSink

auditoria = ApiAudit([InMemoryAuditSink(), LoggingAuditSink()], meter=modulo_observabilidad.meter)
```

## 5. La auditoría no se muestrea

Las trazas **sí** se muestrean (`sampling_ratio`, [ADR-008](../architecture/adr/ADR-008-enterprise-observability-stack.md)) porque son telemetría estadística: con el 10% de las trazas se diagnostica igual de bien.

La auditoría **no**. Es un registro de cumplimiento con requisitos de retención propios, y perder una de cada diez entradas la invalidaría por completo — justo la entrada perdida sería la que hiciera falta en una investigación. Por eso `AuditSink` es un contrato distinto de `Exporter` y no comparte su pipeline.

## 6. Destinos

`AuditSink` son dos miembros: `name` y `emit()`. TEAF trae dos implementaciones:

| Destino | Para qué |
|---|---|
| `InMemoryAuditSink` | Desarrollo, pruebas e inspección desde el propio proceso (`sink.records`). Historial acotado. |
| `LoggingAuditSink` | Emite cada entrada como log estructurado. Con `log_format="json"` sale una línea JSON con correlation/trace/span-id ya incluidos, lista para cualquier agente de logs. |

Un destino propio —una tabla de auditoría vía el `DatabaseModule`, un SIEM, una cola— es implementar esos dos miembros:

```python
from teaf.api import ApiAudit, ApiAuditRecord, AuditSink

class SiemAuditSink(AuditSink):
    @property
    def name(self) -> str:
        return "siem"

    async def emit(self, record: ApiAuditRecord) -> None:
        await self._cliente.enviar(record.as_dict())

auditoria = ApiAudit([SiemAuditSink()])
```

### Un destino que falla no tumba la API

Si `emit()` lanza, `ApiAudit` lo registra en el log y **sigue** con los demás destinos. Perder una API entera porque un SIEM está caído sería peor que perder una entrada de auditoría en ese destino.

Del mismo modo, una auditoría **sin destinos** no falla: registra un aviso una sola vez y sigue publicando el evento. Una auditoría mal configurada nunca debe tumbar la API que audita.

## 7. Configuración por entorno

```bash
API_AUDIT_ENABLED=true
API_AUDIT_MEMORY_SINK_ENABLED=true
API_AUDIT_MEMORY_SINK_LIMIT=1000
API_AUDIT_LOGGING_SINK_ENABLED=false
```

En **producción**, `api_audit_logging_sink_enabled` viene activado por defecto (`ProductionSettings`): es donde un agente de logs puede recoger la auditoría y retenerla, a diferencia del destino en memoria, que se pierde al reiniciar el proceso.

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa y el orden de la cadena.
- [OBSERVABILITY.md](../observability/OBSERVABILITY.md) — la plataforma con la que se cruza.
- [LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md) — el formato del log estructurado.
- [`examples/api-audit/`](../../examples/api-audit/) — ejemplo ejecutable.
