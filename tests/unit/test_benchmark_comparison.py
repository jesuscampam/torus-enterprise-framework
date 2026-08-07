"""Pruebas de la comparación contra baseline de la suite de benchmarks (Sprint 2.9.1).

La comparación decide si una puerta de calidad pasa o falla, así que sus
reglas — mínimo en vez de mediana, suelo absoluto de ruido, confirmación de
sospechosos — son lógica de producto y no un detalle de la herramienta. Se
prueban aquí porque su modo de fallo natural es silencioso en ambos
sentidos: una regresión que no se reporta, o ruido que hace fallar la
puerta hasta que alguien la desactiva.
"""

from __future__ import annotations

import pytest
from benchmarks.__main__ import NOISE_FLOOR_US, compare, confirm_regressions
from benchmarks.harness import BenchmarkResult


def _result(name: str, min_us: float, *, group: str = "grupo") -> BenchmarkResult:
    """Resultado con el mínimo bajo control; el resto de campos no influyen."""
    return BenchmarkResult(
        name=name,
        group=group,
        median_us=min_us * 2,
        p95_us=min_us * 3,
        min_us=min_us,
        repeats=50,
    )


def _baseline(**mins: float) -> dict[str, object]:
    return {
        "results": [
            {"name": name, "minUs": value, "medianUs": value * 2} for name, value in mins.items()
        ]
    }


def test_compare_detects_regression_beyond_tolerance() -> None:
    regressions, improvements = compare([_result("op", 200.0)], _baseline(op=100.0), tolerance=0.60)
    assert improvements == []
    assert len(regressions) == 1
    assert "op" in regressions[0]
    assert "+100%" in regressions[0]


def test_compare_detects_improvement_beyond_tolerance() -> None:
    regressions, improvements = compare([_result("op", 20.0)], _baseline(op=100.0), tolerance=0.60)
    assert regressions == []
    assert len(improvements) == 1
    assert "-80%" in improvements[0]


def test_compare_ignores_change_within_tolerance() -> None:
    assert compare([_result("op", 130.0)], _baseline(op=100.0), tolerance=0.60) == ([], [])


def test_compare_uses_the_minimum_not_the_median() -> None:
    """El mínimo baja pero la mediana sube: debe contar el mínimo.

    Es exactamente la forma del ruido que motivó el cambio — un pico del
    anfitrión desplaza la mediana sin tocar el coste real de la operación.
    """
    noisy = BenchmarkResult(
        name="op", group="g", median_us=1000.0, p95_us=2000.0, min_us=20.0, repeats=50
    )
    regressions, improvements = compare([noisy], _baseline(op=100.0), tolerance=0.60)
    assert regressions == []
    assert len(improvements) == 1


def test_compare_ignores_sub_microsecond_swing_below_the_noise_floor() -> None:
    """0.36 µs → 0.60 µs es +66%, pero solo 0.24 µs: es ruido, no regresión."""
    assert compare([_result("op", 0.60)], _baseline(op=0.36), tolerance=0.60) == ([], [])


def test_compare_applies_the_noise_floor_to_improvements_too() -> None:
    assert compare([_result("op", 0.10)], _baseline(op=0.90), tolerance=0.60) == ([], [])


def test_compare_reports_regression_just_above_the_noise_floor() -> None:
    before = 1.0
    regressions, _ = compare(
        [_result("op", before + NOISE_FLOOR_US + 0.01)], _baseline(op=before), tolerance=0.60
    )
    assert len(regressions) == 1


def test_compare_falls_back_to_median_for_pre_sprint_291_baselines() -> None:
    """Las baselines antiguas no guardaban ``minUs``; no deben invalidarse."""
    legacy: dict[str, object] = {"results": [{"name": "op", "medianUs": 100.0}]}
    regressions, _ = compare([_result("op", 300.0)], legacy, tolerance=0.60)
    assert len(regressions) == 1


def test_compare_ignores_a_benchmark_absent_from_the_baseline() -> None:
    """Un benchmark nuevo no tiene con qué compararse — no es una regresión."""
    assert compare([_result("nuevo", 999.0)], _baseline(otro=1.0), tolerance=0.60) == ([], [])


def test_compare_ignores_a_malformed_baseline() -> None:
    assert compare([_result("op", 999.0)], {"results": "no es una lista"}, tolerance=0.60) == (
        [],
        [],
    )


def test_compare_does_not_divide_by_a_zero_baseline() -> None:
    assert compare([_result("op", 10.0)], _baseline(op=0.0), tolerance=0.60) == ([], [])


def test_confirm_discards_noise_that_does_not_reproduce(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un sospechoso que al volver a medir cae en la baseline se descarta."""
    monkeypatch.setattr(
        "benchmarks.__main__.ALL_SUITES", (("falsa", lambda: [_result("op", 100.0)]),)
    )
    confirmed, discarded = confirm_regressions(
        {"op"}, {"falsa": [_result("op", 500.0)]}, _baseline(op=100.0), tolerance=0.60
    )
    assert confirmed == []
    assert discarded == ["op"]


def test_confirm_keeps_a_regression_that_reproduces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "benchmarks.__main__.ALL_SUITES", (("falsa", lambda: [_result("op", 500.0)]),)
    )
    confirmed, discarded = confirm_regressions(
        {"op"}, {"falsa": [_result("op", 500.0)]}, _baseline(op=100.0), tolerance=0.60
    )
    assert discarded == []
    assert len(confirmed) == 1
    assert "op" in confirmed[0]


def test_confirm_only_repeats_suites_containing_a_suspect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Volver a medir debe costar en proporción al problema, no la suite entera."""
    ejecutadas: list[str] = []

    def _suite(nombre: str, resultado: BenchmarkResult):
        def _run() -> list[BenchmarkResult]:
            ejecutadas.append(nombre)
            return [resultado]

        return _run

    monkeypatch.setattr(
        "benchmarks.__main__.ALL_SUITES",
        (
            ("con-sospechoso", _suite("con-sospechoso", _result("op", 500.0))),
            ("sin-sospechoso", _suite("sin-sospechoso", _result("otra", 1.0))),
        ),
    )
    confirm_regressions(
        {"op"},
        {"con-sospechoso": [_result("op", 500.0)], "sin-sospechoso": [_result("otra", 1.0)]},
        _baseline(op=100.0),
        tolerance=0.60,
    )
    assert ejecutadas == ["con-sospechoso"]
