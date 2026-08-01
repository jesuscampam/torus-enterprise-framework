# monitoring/

Observabilidad del backend, en cumplimiento del principio Observability First, instrumentada con **OpenTelemetry**.

## Responsabilidad

- Instrumentación de trazas distribuidas (`traceId`) propagadas a través de `api → services → repository → database` y hacia integraciones salientes.
- Exposición de métricas técnicas y de negocio (latencia, tasa de error, saturación de recursos).
- Health checks (`/health`, `/ready`) usados por el orquestador (Azure App Service, Docker) para verificar disponibilidad.
- Configuración de exportadores compatibles con el backend de observabilidad de producción (Azure Monitor u otro compatible con OpenTelemetry).

## Qué NO debe contener

- Lógica de negocio.
- Decisiones de enrutamiento o autorización.

## Relación con `LOGGING-STANDARD.md`

El detalle completo de niveles de log, correlation-id y qué no debe registrarse está normado en [LOGGING-STANDARD.md](../../docs/standards/LOGGING-STANDARD.md); esta carpeta es donde dicha instrumentación se implementa técnicamente.
