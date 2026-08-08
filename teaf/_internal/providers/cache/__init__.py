"""Proveedores de caché distribuida — implementaciones de ``contracts/cache.py``.

``memory.py`` es la implementación por defecto (un proceso, sin
infraestructura); ``redis.py`` la distribuida, que requiere el extra
opcional ``teaf[redis]``. Ver
[ADR-012](../../../../docs/architecture/adr/ADR-012-redis-optional-infrastructure.md).
"""

from __future__ import annotations
