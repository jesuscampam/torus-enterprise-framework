"""Pruebas de ``SecurityHeadersMiddleware`` (Sprint 2.9.2, ADR-010).

Comprueban **valores reales**, no que el middleware exista. La razón es
directa: hasta Sprint 2.9.2 `Settings` declaraba `security_headers_enabled`
sin que nadie lo leyera, y ninguna prueba lo detectó porque ninguna miraba
las cabeceras de una respuesta real. Una prueba que solo verificara que la
clase se puede instanciar habría seguido pasando con el defecto presente.

Cubren, además de la política en sí, las cuatro interacciones que
SECURITY-STANDARD.md §7 deja abiertas y que ADR-010 decide: respuestas de
error, documentación interactiva, endpoints de salud y OpenAPI.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from teaf._internal.config.settings import TestingSettings
from teaf._internal.core.application import create_app
from teaf._internal.middleware.security_headers import (
    SecurityHeadersMiddleware,
    is_documentation_path,
)

#: Las cuatro cabeceras que exige SECURITY-STANDARD.md §7.
CONTENT_TYPE_OPTIONS = "x-content-type-options"
FRAME_OPTIONS = "x-frame-options"
CONTENT_SECURITY_POLICY = "content-security-policy"
STRICT_TRANSPORT_SECURITY = "strict-transport-security"


def _client(**overrides: object) -> TestClient:
    return TestClient(create_app(settings=TestingSettings(**overrides)))


# -- Política, sin levantar aplicación ---------------------------------------------------


def test_policy_includes_the_four_headers_required_by_the_standard() -> None:
    middleware = SecurityHeadersMiddleware(app=None)  # type: ignore[arg-type]
    names = dict(middleware.headers_for(path="/health", secure=True))
    assert set(names) == {
        CONTENT_TYPE_OPTIONS,
        FRAME_OPTIONS,
        CONTENT_SECURITY_POLICY,
        STRICT_TRANSPORT_SECURITY,
    }


def test_policy_is_empty_when_disabled() -> None:
    middleware = SecurityHeadersMiddleware(app=None, enabled=False)  # type: ignore[arg-type]
    assert middleware.headers_for(path="/health", secure=True) == ()


def test_hsts_is_omitted_over_plain_http() -> None:
    """RFC 6797 §7.2 lo prohíbe explícitamente sobre transporte no seguro."""
    middleware = SecurityHeadersMiddleware(app=None)  # type: ignore[arg-type]
    assert STRICT_TRANSPORT_SECURITY not in dict(
        middleware.headers_for(path="/health", secure=False)
    )


def test_hsts_is_omitted_when_max_age_is_zero() -> None:
    middleware = SecurityHeadersMiddleware(app=None, hsts_max_age_seconds=0)  # type: ignore[arg-type]
    assert STRICT_TRANSPORT_SECURITY not in dict(
        middleware.headers_for(path="/health", secure=True)
    )


def test_frame_options_is_omitted_when_configured_empty() -> None:
    """Cadena vacía significa «no la emitas» — ``frame-ancestors`` ya cubre el caso."""
    middleware = SecurityHeadersMiddleware(app=None, frame_options="")  # type: ignore[arg-type]
    assert FRAME_OPTIONS not in dict(middleware.headers_for(path="/health", secure=True))


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/docs/oauth2-redirect", "/redoc/algo"])
def test_documentation_paths_are_recognised(path: str) -> None:
    assert is_documentation_path(path) is True


@pytest.mark.parametrize("path", ["/", "/health", "/openapi.json", "/documentos", "/redocx"])
def test_non_documentation_paths_are_not_recognised(path: str) -> None:
    assert is_documentation_path(path) is False


# -- Comportamiento sobre la aplicación real ---------------------------------------------


def test_headers_are_present_on_a_normal_response() -> None:
    with _client() as client:
        response = client.get("/health")
    assert response.headers[CONTENT_TYPE_OPTIONS] == "nosniff"
    assert response.headers[FRAME_OPTIONS] == "DENY"
    assert response.headers[CONTENT_SECURITY_POLICY] == "default-src 'none'; frame-ancestors 'none'"


def test_headers_are_absent_when_disabled() -> None:
    with _client(security_headers_enabled=False) as client:
        response = client.get("/health")
    for header in (CONTENT_TYPE_OPTIONS, FRAME_OPTIONS, CONTENT_SECURITY_POLICY):
        assert header not in response.headers


def test_headers_reach_error_responses() -> None:
    """Una respuesta de error la genera una capa más interna que este middleware."""
    with _client() as client:
        response = client.get("/no-existe")
    assert response.status_code == 404
    assert response.headers[CONTENT_TYPE_OPTIONS] == "nosniff"
    assert response.headers[CONTENT_SECURITY_POLICY]


def test_frame_options_honours_configuration() -> None:
    with _client(security_frame_options="SAMEORIGIN") as client:
        response = client.get("/health")
    assert response.headers[FRAME_OPTIONS] == "SAMEORIGIN"


def test_content_security_policy_honours_configuration() -> None:
    politica = "default-src 'self'; img-src 'self' data:"
    with _client(security_content_security_policy=politica) as client:
        response = client.get("/health")
    assert response.headers[CONTENT_SECURITY_POLICY] == politica


def test_hsts_is_emitted_over_https_only() -> None:
    app = create_app(settings=TestingSettings())
    with TestClient(app, base_url="https://testserver") as client:
        seguro = client.get("/health")
    with TestClient(app, base_url="http://testserver") as client:
        inseguro = client.get("/health")
    assert seguro.headers[STRICT_TRANSPORT_SECURITY] == "max-age=31536000"
    assert STRICT_TRANSPORT_SECURITY not in inseguro.headers


def test_hsts_max_age_honours_configuration() -> None:
    app = create_app(settings=TestingSettings(security_hsts_max_age_seconds=600))
    with TestClient(app, base_url="https://testserver") as client:
        response = client.get("/health")
    assert response.headers[STRICT_TRANSPORT_SECURITY] == "max-age=600"


def test_documentation_keeps_working_without_a_blocking_csp() -> None:
    """Swagger UI carga sus propios recursos: una CSP ``default-src 'none'`` la rompería."""
    with _client() as client:
        docs = client.get("/docs")
    assert docs.status_code == 200
    assert CONTENT_SECURITY_POLICY not in docs.headers
    #: Las demás cabeceras sí se aplican también a la documentación.
    assert docs.headers[CONTENT_TYPE_OPTIONS] == "nosniff"


# -- Ausencia de regresión ---------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/health", "/live", "/ready", "/info"])
def test_body_and_status_are_unchanged_by_the_middleware(path: str) -> None:
    """El middleware solo debe añadir cabeceras: cuerpo y estado, intactos."""
    with _client() as with_headers, _client(security_headers_enabled=False) as without:
        activo = with_headers.get(path)
        inactivo = without.get(path)
    assert activo.status_code == inactivo.status_code
    assert activo.content == inactivo.content
    assert activo.headers["content-type"] == inactivo.headers["content-type"]


def test_runtime_info_shape_is_unchanged_by_the_middleware() -> None:
    """``/runtime/info`` lleva tiempo de actividad, así que se compara su forma.

    Dos instancias distintas de la aplicación nunca darán el mismo byte en ese
    campo; exigirlo convertiría la prueba en intermitente sin detectar nada.
    """
    with _client() as with_headers, _client(security_headers_enabled=False) as without:
        activo = with_headers.get("/runtime/info")
        inactivo = without.get("/runtime/info")
    assert activo.status_code == inactivo.status_code
    assert activo.json().keys() == inactivo.json().keys()
    assert activo.json()["frameworkVersion"] == inactivo.json()["frameworkVersion"]


def test_openapi_schema_is_unchanged_by_the_middleware() -> None:
    with _client() as with_headers, _client(security_headers_enabled=False) as without:
        assert with_headers.get("/openapi.json").json() == without.get("/openapi.json").json()


def test_health_endpoints_keep_their_payload() -> None:
    with _client() as client:
        assert client.get("/health").json()["status"] == "ok"
        assert client.get("/live").status_code == 200
        assert client.get("/ready").status_code == 200


def test_an_application_header_is_never_overwritten() -> None:
    """Si un endpoint fija su propia política, manda el endpoint."""
    app = create_app(settings=TestingSettings())

    @app.get("/propia")
    async def propia() -> dict[str, str]:
        from fastapi.responses import JSONResponse  # noqa: PLC0415

        return JSONResponse(  # type: ignore[return-value]
            {"ok": True}, headers={CONTENT_SECURITY_POLICY: "default-src 'self'"}
        )

    with TestClient(app) as client:
        response = client.get("/propia")
    assert response.headers[CONTENT_SECURITY_POLICY] == "default-src 'self'"
