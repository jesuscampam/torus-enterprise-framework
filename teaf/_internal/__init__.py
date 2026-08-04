"""Implementación interna de TEAF — namespace privado.

Todo lo que cuelga de ``teaf._internal`` (``core``, ``runtime``, ``sdk``,
``contracts``, ``providers``, ``config``, ``modules``, ``middleware``,
``monitoring``, ``developer``, ``shared``, ...) es implementación privada
del framework, sin ninguna garantía de estabilidad entre versiones fuera de
lo que ``teaf/`` (las fachadas en la raíz del paquete) reexporta
explícitamente. Nunca se importa directamente desde fuera de este
repositorio — ver docs/public-api/IMPORT-GUIDE.md.

Movido desde el antiguo paquete de nivel superior ``backend/`` en el
Sprint 2.6.2 (ver docs/architecture/adr/ADR-006-internal-namespace-refactor.md)
para eliminar el riesgo de colisión de namespace con un posible paquete
``backend/`` propio de una aplicación consumidora. Ver también
teaf/_internal/README.md.
"""

from __future__ import annotations
