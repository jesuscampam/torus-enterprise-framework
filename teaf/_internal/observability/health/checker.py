"""``CompositeHealthChecker`` — agrega ``HealthCheck``/``ModuleHealth`` en un ``HealthReport``.

Un ``HealthCheck`` sin ``check`` (``None``) o cuyo ``check()`` lance una
excepción cuenta como ``CapabilityHealth.UNHEALTHY`` — un módulo que no
puede ni siquiera reportar su propio estado no es "desconocido", es una
señal de fallo real. El resultado global (``HealthReport.overall``) es el
peor estado entre los checks marcados ``critical=True`` (los no críticos
aparecen en el desglose pero no degradan el resultado agregado — mismo
criterio que documenta ``observability/models.py::HealthCheck``).
"""

from __future__ import annotations

from collections.abc import Sequence

from teaf._internal.observability.models import HealthCheck, HealthReport
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.sdk.health import ModuleHealth
from teaf._internal.sdk.module_base import ModuleBase

#: Orden de severidad, peor a mejor — el agregado toma el primero presente.
_SEVERITY_ORDER: tuple[CapabilityHealth, ...] = (
    CapabilityHealth.UNHEALTHY,
    CapabilityHealth.DEGRADED,
    CapabilityHealth.UNKNOWN,
    CapabilityHealth.HEALTHY,
)


def _evaluate(check: HealthCheck) -> CapabilityHealth:
    if check.check is None:
        return CapabilityHealth.UNKNOWN
    try:
        return check.check()
    except Exception:  # noqa: BLE001 — un check no debe poder tumbar /health
        return CapabilityHealth.UNHEALTHY


def _from_module_health(module_id: str, module_health: ModuleHealth) -> HealthCheck:
    return HealthCheck(
        name=f"{module_id}.{module_health.name}",
        check=module_health.check,
        description=module_health.description,
    )


class CompositeHealthChecker:
    """Evalúa un conjunto fijo de ``HealthCheck`` y agrega el resultado."""

    def __init__(self, checks: Sequence[HealthCheck] = ()) -> None:
        self._checks = tuple(checks)

    @classmethod
    def from_modules(cls, modules: Sequence[ModuleBase]) -> CompositeHealthChecker:
        """Construye el checker a partir de los ``health_checks`` declarados por cada módulo."""
        checks: list[HealthCheck] = []
        for module in modules:
            module_id = module.get_manifest().descriptor.id
            for module_health in module.get_manifest().health_checks:
                checks.append(_from_module_health(module_id, module_health))
        return cls(checks)

    @property
    def checks(self) -> tuple[HealthCheck, ...]:
        return self._checks

    def check_all(self) -> HealthReport:
        """Evalúa cada ``HealthCheck`` y agrega el resultado (peor estado crítico gana)."""
        results = {check.name: _evaluate(check) for check in self._checks}
        critical_results = [results[check.name] for check in self._checks if check.critical]
        overall = CapabilityHealth.HEALTHY
        for severity in _SEVERITY_ORDER:
            if severity in critical_results:
                overall = severity
                break
        return HealthReport(overall=overall, checks=results)
