"""Runtime del Framework — infraestructura de ejecución de módulos.

Paquete nuevo del Sprint 2.3, construido sobre ``backend/core/`` (kernel) y
paralelo a ``backend/contracts/``/``backend/providers/`` (Sprint 2.2). El
Runtime es deliberadamente **independiente de implementaciones concretas**:
ningún archivo de este paquete importa ``backend/contracts/`` ni
``backend/providers/`` — el ``ServiceContainer`` resuelve por cualquier
``type`` (contrato o no), y el resto de piezas (ciclo de vida, pipelines,
event bus, plugin loader) operan sobre abstracciones genéricas.

Ver docs/runtime/RUNTIME.md.
"""

from __future__ import annotations

#: Versión de la Runtime API (``backend/runtime/api.py`` y las primitivas
#: consumidas por ``backend/sdk/``) — independiente de ``FRAMEWORK_VERSION``
#: (``backend/core/application.py``) y de ``SDK_VERSION``
#: (``backend/sdk/__init__.py``), igual que ambas. Un módulo o un
#: consumidor externo puede declarar compatibilidad contra un rango de esta
#: versión sin acoplarse a la versión de release del framework (ver
#: Sprint 2.5.1, docs/public-api/VERSIONING.md).
RUNTIME_VERSION = "1.0.0"
