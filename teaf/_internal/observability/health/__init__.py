"""Health checks compuestos — agrega los ``ModuleHealth`` de cada módulo bootstrapeado.

Cierra la brecha documentada en ``teaf._internal.sdk.health.ModuleHealth``
("ningún scheduler ni endpoint invoca estas funciones todavía", Sprint
2.5): ``CompositeHealthChecker`` (``checker.py``) es ese consumidor —
``monitoring/health.py`` lo usa para poblar ``/health``/``/ready``/``/live``
con el estado real de cada módulo, en vez de responder de forma estática.
"""

from __future__ import annotations
