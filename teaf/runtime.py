"""``teaf.runtime`` — el orquestador de ciclo de vida del framework.

Fachada sobre ``backend/runtime/runtime.py`` (Sprint 2.3). La mayoría de
los consumidores nunca instancian ``Runtime`` directamente — ``teaf.Application``
(``teaf/application.py``) ya construye y expone uno vía ``.runtime``. Se
reexporta aquí para quien necesite construir un ``Runtime`` de forma
independiente (por ejemplo, en pruebas de un módulo propio).
"""

from __future__ import annotations

from backend.runtime.runtime import Runtime

__all__ = ["Runtime"]
