# Estándar de Logging — TEAF

Este documento define las convenciones obligatorias de logging y trazabilidad del framework, en cumplimiento del principio **Observability First**, apoyado en **OpenTelemetry** (ver [docs/architecture/STACK.md](../architecture/STACK.md)).

## 1. Logging estructurado

- Todo log se emite en formato **JSON estructurado**, nunca como texto libre concatenado, para permitir indexación y búsqueda en el sistema centralizado de logs.
- Campos mínimos obligatorios en cada entrada de log:

```json
{
  "timestamp": "2026-08-01T14:32:10.123Z",
  "level": "INFO",
  "service": "teaf-backend",
  "correlationId": "b3f1c2e4-9a11-4d2f-8b3a-6f2e1d4c9a01",
  "traceId": "4bf92f3577b34da6a3ce929d0e0e4736",
  "message": "Incidente creado correctamente",
  "context": { "incidentId": "..." }
}
```

## 2. Correlation ID y Trace ID

- `middleware/` genera (o propaga, si ya viene del cliente vía header `X-Correlation-Id`) un **correlation-id** único por petición HTTP, presente en todos los logs emitidos durante esa petición.
- El **trace-id** de OpenTelemetry se propaga automáticamente a través de toda la cadena de llamadas (`api → services → repository → database`, y hacia integraciones salientes), permitiendo reconstruir el recorrido completo de una petición en el backend de observabilidad.
- Toda respuesta de error de la API incluye el `correlationId` correspondiente (ver `API-STANDARD.md`), permitiendo a soporte/operaciones localizar los logs exactos de un incidente reportado por un usuario.

## 3. Niveles de log

| Nivel | Uso |
|---|---|
| `DEBUG` | Detalle técnico útil solo en desarrollo; deshabilitado por defecto en producción. |
| `INFO` | Eventos de negocio relevantes (creación de recursos, cambios de estado) y ciclo de vida de la aplicación. |
| `WARNING` | Situación anómala pero recuperable (reintento de integración, degradación parcial). |
| `ERROR` | Fallo que impide completar una operación solicitada; requiere atención pero no compromete la disponibilidad general. |
| `CRITICAL` | Fallo que compromete la disponibilidad o integridad del sistema; requiere atención inmediata. |

- En producción, el nivel mínimo por defecto es `INFO`; el nivel se configura vía `config/` por entorno, nunca hardcodeado.

## 4. Qué NO debe loguearse nunca

- Contraseñas, tokens JWT completos, claves API o cualquier secreto.
- Datos personales sensibles (PII) más allá de identificadores técnicos (IDs); si un log necesita contexto de negocio con datos personales, se registra el identificador, no el dato en claro.
- Payloads completos de peticiones que puedan contener información sensible sin enmascarar.
- Cualquier dato cuyo registro viole `SECURITY-STANDARD.md`.

## 5. Logging por capa

- `middleware/` registra entrada/salida de cada petición HTTP (método, ruta, status, duración, correlation-id) en `INFO`.
- `services/` registra eventos de negocio relevantes (creación, transición de estado, decisiones de negocio significativas) en `INFO`, y condiciones anómalas en `WARNING`/`ERROR`.
- `repository/` no debe emitir logs de negocio; solo `DEBUG` técnico si es estrictamente necesario para diagnóstico de acceso a datos.
- `webhooks/` y `scheduler/` registran cada ejecución (inicio, resultado, duración) para permitir auditar procesos asíncronos que no tienen un usuario esperando respuesta síncrona.

## 6. Métricas

Además de logs y trazas, `monitoring/` expone métricas estándar vía OpenTelemetry:

- Latencia y tasa de error por endpoint.
- Saturación de pool de conexiones a base de datos.
- Tasa de ejecución/fallo de jobs (`scheduler/`) y webhooks (`webhooks/`).
- Métricas de negocio agregadas cuando sea relevante (por ejemplo, volumen de eventos procesados), sin datos sensibles.

## 7. Destino y retención de logs

- En producción, los logs se exportan a un backend centralizado compatible con OpenTelemetry (Azure Monitor u otro backend compatible), nunca se dependen exclusivamente de logs en disco local del contenedor (alineado con Cloud Ready).
- La política de retención se define por entorno: mínima en desarrollo, y conforme a requisitos de auditoría/cumplimiento en producción (a formalizar en la Versión 5 del roadmap, hardening empresarial).

## 8. Sampling de trazas

- En entornos de alto volumen, se aplica sampling de trazas (no de logs de error, que siempre se capturan al 100%) para controlar el volumen sin perder visibilidad estadística del comportamiento del sistema.
