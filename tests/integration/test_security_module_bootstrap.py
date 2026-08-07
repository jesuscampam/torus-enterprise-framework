"""Prueba de integración: ``SecurityModule`` contra un ``Runtime``/``Application`` reales.

Mismo criterio que ``test_database_module_bootstrap.py`` (Sprint 2.6): demuestra
que ``SecurityModule`` — construido enteramente sobre el Module SDK — se registra,
arranca y opera contra el ``Runtime`` real sin llamadas directas a
``ServiceContainer``/``CapabilityRegistry``, y que ``SecurityMiddleware`` puede
configurarse a partir de sus atributos públicos antes de que arranque el ciclo
de vida ASGI (el patrón de cableado documentado en ``teaf/security.py``).
"""

from __future__ import annotations

from fastapi import Depends
from fastapi.testclient import TestClient
from teaf import Application
from teaf._internal.modules.security.module import SecurityModule
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf._internal.sdk.lifecycle import ModuleLifecycleState
from teaf.security import Principal, SecurityMiddleware, current_principal


def test_security_module_constructs_all_its_providers_eagerly() -> None:
    module = SecurityModule()
    provider_ids = {p.provider_id for p in module.provider_registry.providers}
    assert provider_ids == {"anonymous", "jwt", "api-key"}
    assert module.principal_resolver is not None
    assert module.token_provider is not None
    assert module.api_key_provider is not None
    assert module.password_hasher is not None
    assert module.crypto_provider is not None


def test_security_module_manifest_declares_expected_capabilities_and_services() -> None:
    module = SecurityModule()
    manifest = module.get_manifest()

    assert manifest.descriptor.id == "security"
    capability_ids = {c.id for c in manifest.capabilities}
    assert capability_ids == {
        "security",
        "security.authentication",
        "security.authorization",
        "security.tokens",
        "security.crypto",
    }
    assert len(manifest.services) == 3
    assert len(manifest.health_checks) == 1


def test_security_module_bootstraps_via_application_and_reaches_ready() -> None:
    module = SecurityModule()
    app = Application(modules=[module])

    with TestClient(app.asgi) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert module.lifecycle.state is ModuleLifecycleState.READY
        assert any(m.name == "security" for m in app.runtime.modules)
        assert app.runtime.capability_registry.exists("security.authentication")


def test_security_module_health_becomes_healthy_after_start() -> None:
    module = SecurityModule()
    app = Application(modules=[module])

    with TestClient(app.asgi):
        assert module.health.check() is CapabilityHealth.HEALTHY


def test_security_middleware_wiring_pattern_reads_registry_before_constructing_application() -> (
    None
):
    """El patrón documentado en ``teaf/security.py``: leer
    ``provider_registry``/``principal_resolver`` del módulo ya construido
    (antes de pasarlo a ``Application``) para configurar el middleware."""
    module = SecurityModule()
    provider_registry = module.provider_registry
    principal_resolver = module.principal_resolver

    app = Application(modules=[module])
    app.asgi.add_middleware(
        SecurityMiddleware,
        provider_registry=provider_registry,
        principal_resolver=principal_resolver,
    )

    @app.asgi.get("/whoami")
    def whoami(principal: Principal = Depends(current_principal)) -> dict[str, object]:
        return {"id": principal.id, "isAuthenticated": principal.is_authenticated}

    with TestClient(app.asgi) as client:
        response = client.get("/whoami")
        assert response.status_code == 200
        assert response.json() == {"id": "anonymous", "isAuthenticated": False}


def test_security_module_dispose_closes_oidc_http_clients() -> None:
    import httpx
    from teaf.security import AzureADProvider

    http_client = httpx.AsyncClient()
    azure_provider = AzureADProvider(
        tenant="common", client_id="test-client", http_client=http_client
    )
    module = SecurityModule(identity_providers=[azure_provider])
    app = Application(modules=[module])

    with TestClient(app.asgi):
        pass

    assert http_client.is_closed is True


def test_security_module_with_custom_role_catalog() -> None:
    from teaf._internal.modules.security.configuration import SecurityConfiguration

    configuration = SecurityConfiguration(
        jwt_secret="test-secret-with-at-least-32-bytes!!",
        roles={"admin": frozenset({"users:delete"})},
    )
    module = SecurityModule(configuration)
    app = Application(modules=[module])

    with TestClient(app.asgi):
        assert module.role_resolver is not None
