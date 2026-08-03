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
