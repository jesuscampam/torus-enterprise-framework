# Core del Framework — TEAF

Documentación de la infraestructura base implementada en el Sprint 2.1 (Bootstrap & Core Foundation): la primera capa de código ejecutable de TEAF. Complementa — no reemplaza — [FRAMEWORK-BLUEPRINT.md](../architecture/FRAMEWORK-BLUEPRINT.md), que sigue siendo la arquitectura oficial; este documento explica cómo esa arquitectura se materializó en código.

## 1. Arquitectura del Core

El Sprint 2.1 implementa exclusivamente la infraestructura transversal del framework — ningún módulo de negocio. El código vive en las carpetas ya definidas desde Sprint 1 (ver [ARCHITECTURE.md](../architecture/ARCHITECTURE.md)):

```
backend/
├── main.py                    # Entry point: uvicorn backend.main:app
├── core/
│   ├── application.py         # Application Factory (composition root)
│   ├── exceptions.py          # Jerarquía ApplicationException
│   ├── context.py             # ContextVar del correlation-id
│   ├── logging.py             # Logging estructurado (console/JSON/archivo)
│   ├── version.py             # VersionInfo de la instancia en ejecución
│   └── dependencies.py        # Utilidad singleton_provider() para Depends()
├── config/
│   ├── environment.py         # Enum Environment + validación
│   └── settings.py            # Settings por entorno (Development/Testing/Staging/Production)
├── middleware/
│   ├── request_id.py          # RequestIdMiddleware
│   ├── logging.py             # RequestLoggingMiddleware
│   └── exception_handler.py   # Manejadores RFC 7807
├── monitoring/
│   └── health.py               # Rutas /, /health, /live, /ready
└── shared/
    ├── constants.py            # Constantes centralizadas
    ├── strings.py, identifiers.py, dates.py, validation.py, collections.py
```

Ninguna carpeta nueva se creó fuera de las ya aprobadas en Sprint 1.

## 2. Responsabilidades por pieza

| Pieza | Responsabilidad | No hace |
|---|---|---|
| `core/application.py` | **Composition root**: única función `create_app()` que ensambla configuración, logging, middlewares, manejadores de error y rutas de sistema. | No contiene lógica de negocio ni reglas de dominio. |
| `core/exceptions.py` | Jerarquía base (`ApplicationException` y sus 6 subtipos) de la que heredará toda excepción futura del framework. | `AuthenticationException`/`AuthorizationException` son placeholders — sin uso real hasta `security/` (Sprint 2.2). |
| `core/context.py` | Expone el correlation-id de la petición en curso vía `ContextVar`, consumido por `logging.py` y por los middlewares. | No almacena ningún otro estado global. |
| `core/logging.py` | Logging estructurado (JSON) o legible (consola), con handler de archivo y rotación opcional. Deja el campo `traceId` reservado para OpenTelemetry (no implementado aún). | No conoce `Settings` — recibe primitivos, para permanecer sin dependencias (ver sección 4). |
| `core/version.py` | Construye la identidad (`VersionInfo`) de la instancia en ejecución. | No expone HTTP directamente — eso lo hace `monitoring/health.py`. |
| `core/dependencies.py` | `singleton_provider()`: utilidad genérica para declarar *providers* cacheados por proceso, consumidos por FastAPI vía `Depends()`. | No es un contenedor de DI de terceros — deliberadamente. |
| `config/environment.py` | Lee y valida `ENVIRONMENT`; lanza `ConfigurationException` ante un valor inválido. | No lee ningún otro valor de configuración. |
| `config/settings.py` | `Settings` + 4 subclases (`Development/Testing/Staging/Production`), resueltas vía `get_settings()` (cacheada). | No contiene secretos por defecto; todo se sobrescribe por entorno/`.env`. |
| `middleware/request_id.py` | Genera o propaga el correlation-id, lo expone en `core/context.py` y en el header de respuesta. | No autentica ni autoriza. |
| `middleware/logging.py` | Loguea inicio/fin de cada petición con duración, conforme a `LOGGING-STANDARD.md`. | No decide el formato del log (lo decide `core/logging.py`). |
| `middleware/exception_handler.py` | Traduce `ApplicationException`, errores de validación de FastAPI y cualquier excepción no controlada a RFC 7807. | Nunca expone detalles internos en la respuesta; el detalle completo va al log. |
| `monitoring/health.py` | Expone `/`, `/health`, `/live`, `/ready`. | Sin verificaciones reales de dependencias todavía (no hay base de datos que comprobar). |
| `shared/` | Constantes y utilidades genéricas (strings, UUID, fechas, validación, colecciones) sin lógica de negocio. | No depende de ninguna capa superior. |

## 3. Cómo utilizar el framework

Arrancar en desarrollo (desde la raíz del repositorio):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
uvicorn backend.main:app --reload
```

Verificar: `curl http://localhost:8000/health`.

Ejecutar la suite de pruebas: `python -m pytest`.

### Nota sobre el comando de arranque

El Sprint 2.1 pedía literalmente `uvicorn app.main:app --reload`. Se implementó como `uvicorn backend.main:app --reload` para respetar la estructura de carpetas `backend/` ya aprobada en Sprint 1 (CLAUDE.md prohíbe reorganizar la arquitectura sin aprobación explícita) en vez de introducir un paquete `app/` nuevo y paralelo. Ver el reporte de cierre de Sprint 2.1 para el detalle completo de esta decisión.

## 4. Cómo extender el Core

- **Añadir un parámetro de configuración**: agregar un campo tipado a `Settings` (o a la subclase de entorno correspondiente) en `backend/config/settings.py`. No requiere tocar `environment.py` ni el resto del framework.
- **Añadir un middleware nuevo**: crear el archivo en `backend/middleware/`, registrarlo en `core/application.py` con `app.add_middleware(...)`, respetando el orden ya documentado (Starlette ejecuta el último añadido primero).
- **Añadir una excepción nueva**: heredar de `ApplicationException` (o de un subtipo existente si aplica semánticamente) en `backend/core/exceptions.py`, y añadir su mapeo a código HTTP en `_STATUS_BY_EXCEPTION_TYPE` de `middleware/exception_handler.py`.
- **Añadir una dependencia inyectable**: declarar una factory decorada con `singleton_provider()` (para recursos de ciclo de vida de proceso) o una función simple (para recursos de ciclo de vida por petición), y consumirla vía `Depends()` en el router correspondiente — ver el ejemplo en el docstring de `core/dependencies.py`.
- **Añadir una utilidad genérica**: si es reutilizable entre capas y no contiene lógica de negocio, va en `backend/shared/`; si es específica de un módulo nuevo, va dentro de ese módulo.

Antes de extender el Core con algo que no encaje en los puntos anteriores, consulta [DECISION-TREE.md](../architecture/DECISION-TREE.md) y [EXTENSIBILITY.md](../architecture/EXTENSIBILITY.md).

## 5. Buenas prácticas aplicadas

- **Composition root explícito**: `core/application.py` es el único archivo de `core/` autorizado a importar `config/`, `middleware/` y `monitoring/` — el resto de `core/` permanece sin dependencias, cumpliendo la regla "Core nunca depende de ningún otro módulo" de [FRAMEWORK-BLUEPRINT.md, sección 11](../architecture/FRAMEWORK-BLUEPRINT.md#11-reglas-arquitectónicas).
- **Inyección de configuración, no lectura directa de entorno**: ninguna pieza fuera de `config/` llama a `os.getenv` directamente.
- **Logging y versión sin acoplar a `Settings`**: `core/logging.py` y `core/version.py` reciben primitivos, no el objeto `Settings`, para mantenerse reutilizables y testeables de forma aislada.
- **Errores nunca exponen detalle interno**: todo error 5xx devuelve un mensaje genérico al cliente; el detalle completo (traceback) solo llega al log, correlacionado por `correlationId`.
- **Sin sobre-ingeniería**: no se introdujo un contenedor de DI de terceros, ni un ORM, ni autenticación — exactamente lo que pedía el alcance del Sprint 2.1, ni una línea más.
