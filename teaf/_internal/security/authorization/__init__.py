"""Motor de autorización: RBAC (roles → permisos), resolución de principal y políticas.

``rbac.py`` implementa ``RoleResolver``/``PermissionResolver`` (contracts/
security.py) reutilizando ``Role``/``Permission`` de
``teaf/_internal/providers/security/rbac.py`` (Sprint 2.2); también aporta
``PrincipalResolver``, que combina ambos para construir un ``Principal``
completo a partir de una ``Identity`` ya autenticada — lo usa
``SecurityMiddleware``. ``policy_evaluator.py`` implementa
``PolicyEvaluator``.
"""

from __future__ import annotations
