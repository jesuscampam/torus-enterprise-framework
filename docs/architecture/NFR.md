# Requisitos No Funcionales (NFR) — TEAF

Métricas y atributos de calidad mínimos que todo componente construido sobre TEAF debe cumplir. Complementa [FRAMEWORK-BLUEPRINT.md](FRAMEWORK-BLUEPRINT.md) (secciones 11 y 13) y se verifica en el [Architecture Review Checklist](FRAMEWORK-BLUEPRINT.md#14-architecture-review-checklist) y en [QUALITY-GATES.md](../standards/QUALITY-GATES.md). Estas métricas son objetivos de diseño desde ahora; su medición real solo será posible a partir del código ejecutable de la Versión 1 del [roadmap](../roadmap/ROADMAP.md).

## 1. Métricas mínimas

| Métrica | Objetivo | Se mide en |
|---|---|---|
| Disponibilidad | ≥ 99.9% mensual | Azure Monitor / Application Insights (producción) |
| Tiempo de respuesta (p95) | < 300 ms por endpoint, excluyendo integraciones externas de terceros | Trazas OpenTelemetry (`monitoring/`) |
| Health Check | Responde en < 5 segundos desde el arranque del proceso | `/health`, ver [FRAMEWORK-BLUEPRINT.md, sección 7](FRAMEWORK-BLUEPRINT.md#7-flujo-de-inicialización) |
| Cobertura de pruebas | ≥ 80% en `services/` y `repository/` | CI, ver [CODING-STANDARD.md](../standards/CODING-STANDARD.md) sección 7 |
| Tiempo máximo de inicio | ≤ 30 segundos desde `Application Start` hasta `Ready` | Flujo de inicialización (`startup-flow.mmd`) |
| Logging | 100% de las peticiones generan al menos un log estructurado con `correlationId` | `middleware/`, ver [LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md) |
| Tracing | 100% de las peticiones son trazables de extremo a extremo (`traceId` propagado) | OpenTelemetry, ver [LOGGING-STANDARD.md](../standards/LOGGING-STANDARD.md) sección 2 |

Estas siete métricas son las **mínimas no negociables**; un componente que no pueda cumplirlas debe documentar explícitamente por qué (y por cuánto tiempo) antes de fusionarse, siguiendo la sección "Excepciones" de [QUALITY-GATES.md](../standards/QUALITY-GATES.md).

## 2. Escalabilidad

- Todo componente escala horizontalmente sin afinidad de sesión (Cloud Ready, [ADR-005](adr/ADR-005-cloud-ready.md)).
- El pool de conexiones a base de datos se dimensiona considerando N instancias concurrentes (ver [DATABASE-STANDARD.md](../standards/DATABASE-STANDARD.md), sección 8).
- `Scheduler` y `Webhooks` coordinan su ejecución entre instancias sin duplicar trabajo (ver [FRAMEWORK-BLUEPRINT.md, sección 13](FRAMEWORK-BLUEPRINT.md#13-riesgos-arquitectónicos)).

## 3. Seguridad

- Cumplimiento íntegro de [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md) y de la [arquitectura de seguridad](../diagrams/security-architecture.mmd).
- Ningún secreto fuera de un gestor de secretos (Azure Key Vault en producción).
- Superficie de ataque mínima: solo las rutas explícitamente públicas omiten autenticación.

## 4. Recuperación (Resiliencia / Disaster Recovery)

- Sin estado local crítico: cualquier instancia puede reiniciarse o reemplazarse sin pérdida de datos (Cloud Ready).
- Backups de PostgreSQL con punto de recuperación acorde al RPO/RTO que se defina por aplicación (a formalizar en la Versión 5 del [roadmap](../roadmap/ROADMAP.md), hardening empresarial).
- Toda integración externa (`webhooks/`, conectores) implementa reintentos con backoff ante fallos transitorios.

## 5. Portabilidad

- Docker First ([ADR-003](adr/ADR-003-uso-de-docker.md)): la misma imagen corre en local, Render y Azure App Service sin reconstrucción.
- Database Agnostic a nivel de dominio: solo `repository/`/`database/` conocen detalles de PostgreSQL (ver [DATABASE-STANDARD.md](../standards/DATABASE-STANDARD.md), sección 1).
- `AI` es agnóstico de proveedor (ver [arquitectura de AI Providers](FRAMEWORK-BLUEPRINT.md#4-mapa-general-del-framework)): cambiar de proveedor de LLM no debe requerir cambios en `services/`.

## 6. Observabilidad

- Logging y tracing al 100% (ver tabla de métricas).
- Todo módulo que realiza I/O externo se instrumenta con OpenTelemetry desde su primera versión, no como mejora posterior.
- Correlation ID presente en toda petición, log y traza (ver [`security-architecture.mmd`](../diagrams/security-architecture.mmd)).

## 7. Mantenibilidad

- Toda carpeta documentada con `README.md` de responsabilidad (ya cumplido desde Sprint 1).
- Toda decisión estructural respaldada por un ADR (ver [docs/architecture/adr/](adr/)).
- Complejidad ciclomática y duplicación controladas por lint (`ruff`, `eslint`) y revisión humana (ver [CODING-STANDARD.md](../standards/CODING-STANDARD.md)).

## 8. Compatibilidad Azure

- Contenedores compatibles con Azure App Service (Linux, sin dependencias del sistema operativo host).
- Configuración de secretos compatible con Azure Key Vault desde el diseño (`config/`).
- Observabilidad exportable a Azure Monitor / Application Insights (ver [`deployment-physical.mmd`](../diagrams/deployment-physical.mmd)).

## 9. Compatibilidad Docker

- Todo componente tiene un `Dockerfile` (ver [`docker/`](../../docker/README.md)) con build multi-stage e imagen base fijada explícitamente.
- Arranque y `/health` verificables dentro del contenedor sin dependencias externas al propio `docker-compose` de desarrollo.

## 10. Compatibilidad IA

- Ningún módulo de negocio depende del SDK concreto de un proveedor de IA; todos consumen la interfaz de `ai/` (ver [arquitectura de AI Providers](FRAMEWORK-BLUEPRINT.md#4-mapa-general-del-framework)).
- `AI` nunca accede a `Database` directamente (regla ya fijada en el blueprint, sección 6/11).
- La arquitectura deja espacio explícito para capacidades agénticas futuras (`MCP`) sin romper la interfaz de `AI` ya aceptada.
