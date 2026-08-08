# api-audit/

Auditoría de API en `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)): qué se registra de cada petición y cómo se integra con la plataforma de observabilidad.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- Se auditan las peticiones **correctas, las rechazadas y las fallidas**. Una auditoría que solo viera el tráfico aceptado sería inútil para lo que más importa auditar — por eso `ApiAuditMiddleware` va casi en el exterior de la cadena, solo por dentro de CORS.
- Cada entrada lleva `correlationId`/`traceId`/`spanId`, así que desde la auditoría se salta a la traza completa de la petición sin necesitar correlación externa — ver [AUDIT.md](../../docs/api/AUDIT.md).
- El desenlace (`ApiOutcome`) distingue `accepted`, `rejected` (4xx), `failed` (5xx o excepción) y `replayed` (respuesta idempotente reproducida).
- Varios destinos a la vez: `InMemoryAuditSink` para inspeccionar desde el proceso, `LoggingAuditSink` para que un agente de logs la recoja. Un destino que falle se registra y **no impide** que los demás reciban la entrada.
- **La auditoría nunca se muestrea.** Las trazas sí (`sampling_ratio`, [ADR-008](../../docs/architecture/adr/ADR-008-enterprise-observability-stack.md)) porque son telemetría estadística; la auditoría es un registro de cumplimiento y perder una de cada diez entradas la invalidaría.
- Con un `Meter` de `ObservabilityModule`, `ApiAudit` emite además un contador de peticiones auditadas y un histograma de latencias.
