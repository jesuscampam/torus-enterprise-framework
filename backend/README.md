# Backend — TEAF

Backend del framework, construido sobre **FastAPI** (ver [ADR-001](../docs/architecture/adr/ADR-001-uso-de-fastapi.md)) siguiendo Clean Architecture en capas estrictas. El detalle completo de la arquitectura, el flujo de dependencias y la responsabilidad de cada capa está en [docs/architecture/ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md).

> Esta iteración contiene únicamente la estructura de carpetas. El bootstrap ejecutable (aplicación FastAPI real, dependencias, primer endpoint) se incorpora en la Versión 1 del [roadmap](../docs/roadmap/ROADMAP.md).

## Capas

| Carpeta | Responsabilidad |
|---|---|
| [`api/`](api/README.md) | Contratos HTTP versionados (routers, controladores). |
| [`core/`](core/README.md) | Kernel del framework: bootstrap, inyección de dependencias, excepciones base. |
| [`services/`](services/README.md) | Casos de uso y orquestación de negocio. |
| [`repository/`](repository/README.md) | Acceso a datos abstraído (Repository Pattern). |
| [`database/`](database/README.md) | Motor y sesión de base de datos (SQLAlchemy). |
| [`models/`](models/README.md) | Entidades ORM (persistencia). |
| [`schemas/`](schemas/README.md) | Contratos de entrada/salida de la API (DTOs Pydantic). |
| [`security/`](security/README.md) | Autenticación, autorización, hashing. |
| [`middleware/`](middleware/README.md) | Componentes transversales HTTP. |
| [`monitoring/`](monitoring/README.md) | Observabilidad (OpenTelemetry, health checks). |
| [`shared/`](shared/README.md) | Utilidades y tipos genéricos compartidos. |
| [`config/`](config/README.md) | Configuración por entorno. |
| [`ai/`](ai/README.md) | Abstracciones AI-Ready. |
| [`webhooks/`](webhooks/README.md) | Framework de webhooks entrantes/salientes. |
| [`scheduler/`](scheduler/README.md) | Framework de tareas programadas. |

## Regla de dependencias

Las dependencias siempre apuntan hacia adentro: `api → services → repository → database`. Ninguna capa interna puede importar una capa externa (por ejemplo, `repository/` nunca importa nada de `api/`). Las capas transversales (`core/`, `config/`, `security/`, `middleware/`, `monitoring/`, `shared/`, `ai/`, `webhooks/`, `scheduler/`) pueden ser consumidas por cualquier capa, pero no consumen lógica de negocio de `services/`.
