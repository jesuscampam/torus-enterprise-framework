"""``DefaultPolicyEvaluator`` — implementación de ``PolicyEvaluator`` (contracts/security.py).

Delega en ``Policy.evaluate()`` — la indirección existe para que
``@authorize(policy=...)`` (ver ``teaf/_internal/security/decorators.py``)
dependa del contrato ``PolicyEvaluator``, no de ``Policy`` directamente,
permitiendo sustituir la evaluación (p. ej. con logging o caché de
resultados) sin tocar los decoradores ni las políticas ya definidas.
"""

from __future__ import annotations

from teaf._internal.contracts.security import PolicyEvaluator
from teaf._internal.security.models import Policy, Principal


class DefaultPolicyEvaluator(PolicyEvaluator):
    """Evalúa una ``Policy`` contra un ``Principal`` invocando ``policy.evaluate()``."""

    def evaluate(self, policy: Policy, principal: Principal) -> bool:
        return policy.evaluate(principal)
