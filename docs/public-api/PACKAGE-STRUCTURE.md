# Estructura del Paquete — TEAF

Cómo está organizado `teaf/` y por qué. Ver [PUBLIC-API.md](PUBLIC-API.md) para el catálogo completo de símbolos.

## 1. Árbol

```
teaf/
├── __init__.py        # __all__ — agrega todo, no implementa nada
├── py.typed            # marcador PEP 561 (teaf distribuye anotaciones de tipo)
├── version.py             # FRAMEWORK_VERSION, SDK_VERSION, RUNTIME_VERSION,
│                            # MODULE_SPEC_VERSION, PUBLIC_API_VERSION, Version, is_compatible()
├── application.py           # Application
├── runtime.py                 # Runtime
├── modules.py                   # Module, ModuleBase, ModuleBuilder, ModuleContext,
│                                  # ModuleManifest, ModuleRegistry, ModuleCategory
├── services.py                     # ServiceContainer, Lifetime
├── events.py                         # EventBus, Event
├── capabilities.py                     # CapabilityRegistry, CapabilityCategory
└── health.py                             # Health
```

## 2. Por qué una fachada por concepto, no un único archivo

Cada archivo cubre exactamente un eje del framework (aplicación, runtime, módulos, servicios, eventos, capacidades, salud, configuración, versión) — el mismo particionado que ya usan `backend/sdk/` y `backend/runtime/` internamente. Un desarrollador que solo necesita construir módulos puede leer únicamente `modules.py`; uno que solo necesita inspeccionar servicios, únicamente `services.py`. `teaf/__init__.py` los agrega todos para el caso común (`from teaf import ...`), pero nada impide `from teaf.modules import ModuleBuilder` directamente.

## 3. Regla de cada fachada

Todo archivo de `teaf/` (salvo `__init__.py`) sigue el mismo patrón:

1. Importa desde exactamente los archivos de `backend/` que implementan ese concepto.
2. Opcionalmente define un alias con nombre público (`Module = ModuleBase`, `Health = CapabilityHealth`, `Configuration = Settings`) cuando el nombre interno no es el ideal para la superficie pública.
3. Declara `__all__` con exactamente lo que expone — nunca reexporta un símbolo que no pensó exponer deliberadamente.
4. **Nunca implementa lógica nueva** — ver la única excepción deliberada en la sección 4.

Ninguna fachada importa otra fachada de `teaf/` — todas importan directamente de `backend/`, para que cada una sea comprensible de forma aislada y no haya un orden de import implícito entre ellas (el único archivo que las conoce a todas es `__init__.py`).

## 4. La única excepción: `teaf/version.py`

`version.py` sí contiene algo de lógica propia (`is_compatible()`, la clase `Version`) — no existe un equivalente en `backend/` para agregar porque el concepto de "versión pública consolidada" nace en este Sprint. El resto de constantes que agrega (`FRAMEWORK_VERSION`, `SDK_VERSION`, `RUNTIME_VERSION`, `MODULE_SPEC_VERSION`) sí se originan en `backend/` — ver [VERSIONING.md](VERSIONING.md).

## 5. Por qué `backend/` no importa `teaf/`

La dirección de dependencias es siempre `teaf/ → backend/`, nunca al revés — invertirla (por ejemplo, que `backend/core/application.py` importe `FRAMEWORK_VERSION` desde `teaf.version`) crearía un ciclo real: `teaf/application.py` ya importa `backend.core.application` para construir `Application`, así que si `backend.core.application` importara de vuelta `teaf.version`, cualquiera que importe `backend.core.application` directamente (como ya hacen varias pruebas existentes del framework) dispararía la carga de `teaf/__init__.py`, que a su vez intenta re-importar el propio `backend.core.application` todavía a medio inicializar — `ImportError: cannot import name 'create_app' from partially initialized module`. Mantener `backend/` completamente ajeno a `teaf/` evita esta clase de fallo por construcción.

## 6. `py.typed`

TEAF distribuye sus propias anotaciones de tipo (ver `mypy --strict` en [QUALITY-GATES.md](../standards/QUALITY-GATES.md)) — el archivo vacío `teaf/py.typed` (PEP 561) le indica a `mypy`/`pyright` en un proyecto consumidor que puede confiar en los tipos de `teaf.*` en vez de tratarlo como código sin anotar.
