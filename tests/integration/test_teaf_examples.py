"""Ejecuta cada ejemplo de examples/ como un proceso real y verifica su salida.

Más estricto que solo comprobar que no importan `backend.*` (ver
tests/unit/test_import_boundary_checker.py) — esto prueba que además
funcionan de extremo a extremo tal como los ejecutaría un desarrollador
siguiendo docs/public-api/ o examples/README.md.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"
_EXAMPLE_DIRS = sorted(p for p in _EXAMPLES_DIR.iterdir() if (p / "main.py").exists())


@pytest.mark.parametrize("example_dir", _EXAMPLE_DIRS, ids=lambda p: p.name)
def test_example_runs_successfully(example_dir: Path) -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=example_dir,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_hello_world_prints_the_framework_version() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "hello-world",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "TEAF" in result.stdout
    assert "Runtime state: running" in result.stdout
    assert "Runtime state: stopped" in result.stdout


def test_basic_module_greets_and_registers_its_capability() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "basic-module",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Hola, TEAF." in result.stdout
    assert "Capacidad registrada: True" in result.stdout


def test_application_bootstrap_registers_the_clock_module() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "application-bootstrap",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "Servicios registrados: 1" in result.stdout
    assert "Capacidades registradas: 1" in result.stdout


def test_module_registration_bootstraps_hello_module_automatically() -> None:
    """Sprint 2.6.3 — Module Registration API: sin bootstrap() manual, sin asyncio.run()."""
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "module-registration",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "hello" in result.stdout
    assert "Capacidad 'hello.greet' registrada: True" in result.stdout


def test_jwt_login_issues_a_token_and_protects_an_endpoint() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "jwt-login",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "POST /login -> 401" in result.stdout
    assert "GET /me (con token) -> 200" in result.stdout


def test_api_key_auth_issues_uses_revokes_and_rotates_a_key() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "api-key-auth",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "GET /reports (header) -> 200" in result.stdout
    assert "GET /reports (revocada) -> 401" in result.stdout
    assert "GET /reports (nueva key) -> 200" in result.stdout


def test_ldap_login_maps_a_group_to_a_role() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "ldap-login",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "GET /tickets/close (bind fallido) -> 401" in result.stdout
    assert "GET /tickets/close (bind correcto) -> 200" in result.stdout


def test_azure_ad_login_validates_a_mocked_oidc_token() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "azure-ad-login",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "login.microsoftonline.com" in result.stdout
    assert "GET /me (con token) -> 200" in result.stdout


def test_role_based_endpoint_enforces_the_admin_role() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "role-based-endpoint",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "POST /incidents/42/close -> 403" in result.stdout
    assert "POST /incidents/42/close -> 200" in result.stdout


def test_permission_based_endpoint_enforces_the_permission() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "permission-based-endpoint",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "POST /invoices/7/void -> 403" in result.stdout
    assert "POST /invoices/7/void -> 200" in result.stdout


def test_policy_based_endpoint_enforces_tenant_membership() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "policy-based-endpoint",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "GET /tenants/acme/settings -> 200" in result.stdout
    assert "GET /tenants/acme/settings -> 403" in result.stdout


def test_anonymous_endpoint_contrasts_public_and_protected_routes() -> None:
    result = subprocess.run(
        [sys.executable, "main.py"],
        cwd=_EXAMPLES_DIR / "anonymous-endpoint",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert "GET /status -> 200" in result.stdout
    assert "GET /account -> 401" in result.stdout


def test_discovered_at_least_the_expected_examples() -> None:
    names = {p.name for p in _EXAMPLE_DIRS}
    assert names == {
        "hello-world",
        "basic-module",
        "application-bootstrap",
        "module-registration",
        "jwt-login",
        "api-key-auth",
        "ldap-login",
        "azure-ad-login",
        "role-based-endpoint",
        "permission-based-endpoint",
        "policy-based-endpoint",
        "anonymous-endpoint",
    }
