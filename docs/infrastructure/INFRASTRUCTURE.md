# Infraestructura del Framework — TEAF

Documentación de la infraestructura base implementada en el Sprint 2.2 (Infrastructure Foundation, v0.2.0-alpha): contratos, providers, registro de módulos y la expansión de inyección de dependencias. Complementa — no reemplaza — [FRAMEWORK-BLUEPRINT.md](../architecture/FRAMEWORK-BLUEPRINT.md) y [docs/core/CORE.md](../core/CORE.md) (Sprint 2.1).

> Ningún proveedor real existe todavía: ni base de datos, ni JWT/OAuth, ni IA, ni scheduler, ni storage, ni notificaciones. Este Sprint entrega exclusivamente **contratos e infraestructura abstracta** — el "cómo se conectará", no la conexión en sí.

## 1. Arquitectura

TEAF adopta el patrón **Ports & Adapters** (hexagonal) para toda su infraestructura desde este Sprint:

```
contracts/   →  "puertos": interfaces puras, sin dependencias de terceros.
providers/   →  "adaptadores" (todavía abstractos): clases base y factories
                que un Sprint futuro extenderá con una implementación real
                (SQLAlchemy, JWT, OpenTelemetry, Azure Blob Storage, un
                proveedor de LLM...).
core/registry →  inventario en tiempo de ejecución de qué módulos están
                cableados y con qué madurez (contracts_only / implemented).
```

Esto **no contradice** la responsabilidad ya documentada de `backend/security/`, `backend/database/`, `backend/ai/`, `backend/scheduler/` (Sprint 1): esas carpetas seguirán siendo el hogar de las implementaciones concretas — ahora, esas implementaciones extenderán las clases base de `providers/` y satisfarán las interfaces de `contracts/`, en vez de definir su propia interfaz desde cero. Es un refinamiento de **cómo** se cumple esa responsabilidad, no un cambio de **qué** responsabilidad tiene cada carpeta.

```
backend/
├── contracts/          # Puertos — interfaces puras (Sprint 2.2)
├── providers/           # Adaptadores abstractos (Sprint 2.2)
│   ├── database/
│   ├── security/
│   ├── telemetry/
│   ├── storage/
│   └── ai/
├── security/            # Implementación concreta futura (Sprint 2.3+, hoy solo README)
├── database/             # Implementación concreta futura (Sprint 2.3+, hoy solo README)
├── ai/                    # Implementación concreta futura (Sprint 2.4+, hoy solo README)
└── scheduler/             # Implementación concreta futura (Sprint 2.4+, hoy solo README)
```

## 2. Contracts (`backend/contracts/`)

Interfaces puras (`abc.ABC` + `@abstractmethod`), sin lógica, sin dependencias de terceros — la capa más independiente del framework junto con `core/`.

| Contrato | Archivo | Resumen |
|---|---|---|
| `Repository[T]` | `repository.py` | CRUD genérico con baja lógica (`get_by_id`, `list_paginated`, `add`, `update`, `delete`), ver [DATABASE-STANDARD.md](../standards/DATABASE-STANDARD.md). |
| `UnitOfWork` | `unit_of_work.py` | Gestor de contexto asíncrono para delimitar transacciones (`commit`/`rollback`). |
| `DatabaseProvider` | `database.py` | Ciclo de vida de conexión (`connect`, `disconnect`, `get_session`, `health_check`). |
| `AuthenticationProvider` / `AuthorizationProvider` | `security.py` | Verificación de identidad y decisión de autorización. |
| `TelemetryProvider` | `telemetry.py` | `start_span` (trazas) y `record_metric` (métricas). |
| `StorageProvider` | `storage.py` | `upload`/`download`/`delete`/`exists` sobre archivos/blobs. |
| `AIProvider` | `ai.py` | `generate_text` / `generate_embedding`, agnóstico de proveedor. |
| `SchedulerProvider` | `scheduler.py` | `schedule` (cron) / `run_once` (diferido) / `cancel`. |
| `NotificationProvider` | `notification.py` | `send` por canal (`NotificationChannel`: email/push/chat). |

## 3. Providers (`backend/providers/`)

Clases base y factories **todavía abstractas** que implementan el andamiaje común sobre los contratos, listas para que una implementación concreta (Sprint 2.3+) las extienda.

### `providers/database/`

| Clase | Rol |
|---|---|
| `DatabaseSession` | Forma abstracta de una sesión (`execute`, `flush`, `close`) — preparada para SQLAlchemy 2.x sin importarlo todavía. |
| `ConnectionManager(DatabaseProvider)` | Añade seguimiento de estado (`is_connected`) sobre el contrato. |
| `DatabaseFactory` | Construye un `DatabaseProvider` (`create()`), desacoplando al composition root de la implementación concreta. |
| `RepositoryBase(Repository[T])` | Repositorio base construido sobre una `DatabaseSession` inyectada. |

### `providers/security/`

| Clase | Rol |
|---|---|
| `SecurityContext` | Identidad de seguridad de la petición en curso (`principal_id`, `roles`, `is_authenticated`, `has_permission`) — patrón `ContextVar`, igual que el correlation-id de Sprint 2.1. Valor por defecto: `ANONYMOUS`. |
| `Role` / `Permission` | Abstracciones RBAC mínimas (`rbac.py`). |
| `AuthenticationManager` / `AuthorizationManager` | Orquestan un `AuthenticationProvider`/`AuthorizationProvider` y producen/consumen un `SecurityContext`. |
| `SecurityFactory` | Construye los managers de seguridad de alto nivel. |

### `providers/telemetry/`

| Clase | Rol |
|---|---|
| `TracerProvider` / `MetricsProvider` | Especializaciones de `TelemetryProvider` — cada una implementa una mitad del contrato y deja la otra explícitamente sin soporte (`NotImplementedError`). |
| `LoggerProvider` | Puente futuro entre `backend/core/logging.py` y un backend de observabilidad real. |
| `TelemetryContext` | Reserva `trace_id`/`span_id` de la petición en curso — mismo patrón `ContextVar`, sin traza activa por defecto. |

### `providers/storage/` y `providers/ai/`

Cada uno expone una única clase base (`BaseStorageProvider`, `BaseAIProvider`) que implementa el contrato correspondiente y solo añade un atributo de identidad (`provider_name`) — sin API adicional, a la espera de la primera implementación concreta.

## 4. Module Registry (`backend/core/registry.py`)

`ModuleRegistry` es el inventario **en tiempo de ejecución** de qué subsistemas están cableados en la instancia actual y con qué madurez (`ModuleStatus.CONTRACTS_ONLY` / `IMPLEMENTED`). Complementa a [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md) (que documenta la intención arquitectónica) sin sustituirlo.

Se crea **una vez por instancia de aplicación** (`app.state.module_registry`, cableado en `create_app()`) — deliberadamente **no** como singleton de proceso, para que cada instancia (por ejemplo, una app por test) tenga su propio registro aislado. El Sprint 2.2 registra 7 subsistemas, todos en `contracts_only`: `database`, `security`, `telemetry`, `storage`, `ai`, `scheduler`, `notification`.

Consulta el estado del registro vía **`GET /info`** (`backend/monitoring/info.py`), que también expone la versión del framework (`0.2.0-alpha`).

## 5. Factories

Dos factories abstractas, ambas siguiendo el mismo patrón (método `create*()` sin argumentos, devuelve un contrato):

- **`DatabaseFactory`** (`providers/database/factory.py`): `create() -> DatabaseProvider`.
- **`SecurityFactory`** (`providers/security/factory.py`): `create_authentication_manager() -> AuthenticationManager`, `create_authorization_manager() -> AuthorizationManager`.

Ninguna tiene implementación concreta — ambas son `ABC` y no pueden instanciarse directamente (verificado en `tests/unit/test_providers.py`).

## 6. Expansión de Dependency Injection

`backend/providers/dependencies.py` centraliza los accesores inyectables (`Depends()`) de infraestructura:

| Función | Comportamiento hoy |
|---|---|
| `get_database_provider` / `get_storage_provider` / `get_ai_provider` | Lanzan `InfrastructureException` — seam documentado, sin implementación. |
| `get_security_context` / `get_telemetry_context` | Devuelven un contexto por defecto seguro (anónimo / sin traza) — **ya utilizables hoy**. |
| `get_module_registry` | Lee `request.app.state.module_registry` (ver sección 4). |

`backend/core/dependencies.py` (Sprint 2.1) permanece sin cambios y sin conocer ningún proveedor concreto — sigue siendo la utilidad genérica (`singleton_provider`) sobre la que se construyen estos accesores.

## 7. Extensibilidad

Para implementar un proveedor real en un Sprint futuro:

1. Extender la clase base correspondiente de `providers/<concern>/` (por ejemplo, `ConnectionManager` para un `DatabaseProvider` de SQLAlchemy).
2. Reemplazar el cuerpo de la función de `providers/dependencies.py` correspondiente para que devuelva la implementación real en vez de lanzar `InfrastructureException`.
3. Actualizar la entrada del `ModuleRegistry` en `create_app()` de `CONTRACTS_ONLY` a `IMPLEMENTED`.
4. Añadir la fila correspondiente a [MODULE-CATALOG.md](../architecture/MODULE-CATALOG.md) si el estado documentado cambia.

Ver también [EXTENSIBILITY.md](../architecture/EXTENSIBILITY.md) (Sprint 2.0.1) para las reglas generales de extensión del framework — este documento no las repite, solo las aplica a la infraestructura concreta de este Sprint.

## 8. Qué NO incluye este Sprint

Sin PostgreSQL, sin SQLAlchemy funcional, sin JWT/OAuth, sin usuarios/roles/permisos reales, sin MCP, sin IA real, sin storage real, sin scheduler real, sin Docker ni CI/CD. Todo eso llega en Sprints posteriores (ver [ROADMAP.md](../roadmap/ROADMAP.md)).
