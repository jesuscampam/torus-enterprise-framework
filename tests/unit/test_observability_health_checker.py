"""Pruebas unitarias de teaf/_internal/observability/health/checker.py (CompositeHealthChecker)."""

from __future__ import annotations

from teaf._internal.observability.health.checker import CompositeHealthChecker
from teaf._internal.observability.models import HealthCheck
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase


def test_check_all_with_no_checks_is_healthy() -> None:
    report = CompositeHealthChecker([]).check_all()
    assert report.overall is CapabilityHealth.HEALTHY
    assert report.checks == {}


def test_check_all_aggregates_the_worst_critical_status() -> None:
    checks = [
        HealthCheck(name="a", check=lambda: CapabilityHealth.HEALTHY),
        HealthCheck(name="b", check=lambda: CapabilityHealth.DEGRADED),
    ]
    report = CompositeHealthChecker(checks).check_all()
    assert report.overall is CapabilityHealth.DEGRADED
    assert report.checks == {"a": CapabilityHealth.HEALTHY, "b": CapabilityHealth.DEGRADED}


def test_unhealthy_outranks_degraded() -> None:
    checks = [
        HealthCheck(name="a", check=lambda: CapabilityHealth.DEGRADED),
        HealthCheck(name="b", check=lambda: CapabilityHealth.UNHEALTHY),
    ]
    report = CompositeHealthChecker(checks).check_all()
    assert report.overall is CapabilityHealth.UNHEALTHY


def test_a_check_without_a_callable_is_unknown_but_does_not_crash() -> None:
    report = CompositeHealthChecker([HealthCheck(name="unset", check=None)]).check_all()
    assert report.checks["unset"] is CapabilityHealth.UNKNOWN


def test_a_check_that_raises_counts_as_unhealthy_and_does_not_propagate() -> None:
    def _boom() -> CapabilityHealth:
        raise RuntimeError("dependency unreachable")

    report = CompositeHealthChecker([HealthCheck(name="db", check=_boom)]).check_all()
    assert report.checks["db"] is CapabilityHealth.UNHEALTHY
    assert report.overall is CapabilityHealth.UNHEALTHY


def test_non_critical_checks_appear_in_the_breakdown_but_do_not_degrade_the_overall() -> None:
    checks = [
        HealthCheck(name="critical", check=lambda: CapabilityHealth.HEALTHY),
        HealthCheck(name="informational", check=lambda: CapabilityHealth.UNHEALTHY, critical=False),
    ]
    report = CompositeHealthChecker(checks).check_all()
    assert report.overall is CapabilityHealth.HEALTHY
    assert report.checks["informational"] is CapabilityHealth.UNHEALTHY


class _FakeModule(ModuleBase):
    def __init__(self, module_id: str, status: CapabilityHealth) -> None:
        super().__init__()
        self._module_id = module_id
        self._status = status

    def get_manifest(self) -> ModuleManifest:
        return (
            ModuleBuilder(id=self._module_id, name=self._module_id, display_name=self._module_id)
            .with_version("1.0.0")
            .add_healthcheck(name="ping", check=lambda: self._status)
            .build()
        )


def test_from_modules_builds_one_check_per_module_healthcheck_prefixed_by_module_id() -> None:
    module_a = _FakeModule("a", CapabilityHealth.HEALTHY)
    module_b = _FakeModule("b", CapabilityHealth.DEGRADED)

    checker = CompositeHealthChecker.from_modules([module_a, module_b])
    names = {check.name for check in checker.checks}
    assert names == {"a.ping", "b.ping"}

    report = checker.check_all()
    assert report.overall is CapabilityHealth.DEGRADED
    assert report.checks == {
        "a.ping": CapabilityHealth.HEALTHY,
        "b.ping": CapabilityHealth.DEGRADED,
    }


def test_from_modules_with_no_modules_returns_an_empty_checker() -> None:
    checker = CompositeHealthChecker.from_modules([])
    assert checker.checks == ()
    assert checker.check_all().overall is CapabilityHealth.HEALTHY
