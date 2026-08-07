"""Pruebas unitarias de ``CorsPolicy`` y del versionado de API (Sprint 2.9).

Ambos son objetos de dominio puros —sin I/O y sin HTTP— así que se prueban
directamente, sin cliente ni servidor: los middlewares que los aplican
tienen sus propias pruebas de integración en
``tests/integration/test_api_protection_http.py``.
"""

from __future__ import annotations

import pytest
from teaf.api import (
    ApiVersion,
    ApiVersioningPolicy,
    ApiVersionNegotiator,
    CorsPolicy,
    UnsupportedApiVersionException,
    VersioningStrategy,
)

# -- CORS: orígenes ------------------------------------------------------------------


def test_cors_is_disabled_until_an_origin_is_declared() -> None:
    """Activar la plataforma de protección nunca debe abrir CORS por accidente."""
    assert CorsPolicy().enabled is False
    assert CorsPolicy(allow_origins=("https://a.com",)).enabled is True


def test_an_exact_origin_is_allowed_and_others_are_not() -> None:
    policy = CorsPolicy(allow_origins=("https://app.torus.com",))
    assert policy.is_origin_allowed("https://app.torus.com") is True
    assert policy.is_origin_allowed("https://evil.com") is False


def test_the_wildcard_origin_allows_everything() -> None:
    policy = CorsPolicy(allow_origins=("*",))
    assert policy.is_origin_allowed("https://anything.example") is True
    assert policy.allows_any_origin is True


@pytest.mark.parametrize(
    ("origin", "allowed"),
    [
        ("https://app.torus.com", True),
        ("https://portal.torus.com", True),
        ("https://torus.com", False),
        ("https://evil-torus.com", False),
        ("http://app.torus.com", False),
        ("https://app.torus.com.evil.net", False),
    ],
)
def test_subdomain_wildcards_match_only_real_subdomains(origin: str, allowed: bool) -> None:
    policy = CorsPolicy(allow_origin_patterns=("https://*.torus.com",))
    assert policy.is_origin_allowed(origin) is allowed


# -- CORS: cabeceras de respuesta -----------------------------------------------------


def test_credentials_never_travel_with_a_wildcard_origin() -> None:
    """Regla de seguridad del estándar CORS: con credenciales se responde el
    origen concreto, nunca ``*`` (ver docs/api/CORS.md)."""
    policy = CorsPolicy(allow_origins=("*",), allow_credentials=True)
    headers = policy.response_headers("https://app.torus.com")
    assert headers["Access-Control-Allow-Origin"] == "https://app.torus.com"
    assert headers["Access-Control-Allow-Credentials"] == "true"


def test_a_wildcard_origin_without_credentials_answers_with_the_wildcard() -> None:
    policy = CorsPolicy(allow_origins=("*",))
    headers = policy.response_headers("https://app.torus.com")
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "Access-Control-Allow-Credentials" not in headers


def test_response_headers_always_vary_on_origin() -> None:
    """Sin ``Vary: Origin`` una caché podría servir la respuesta de un origen
    permitido a otro que no lo está."""
    policy = CorsPolicy(allow_origins=("https://a.com",))
    assert policy.response_headers("https://a.com")["Vary"] == "Origin"


def test_a_disallowed_origin_gets_no_cors_headers() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",))
    assert policy.response_headers("https://evil.com") == {}


def test_exposed_headers_are_advertised() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",), expose_headers=("X-Total-Count",))
    headers = policy.response_headers("https://a.com")
    assert headers["Access-Control-Expose-Headers"] == "X-Total-Count"


# -- CORS: preflight ---------------------------------------------------------------------


def test_a_preflight_is_accepted_for_an_allowed_origin_and_method() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",), max_age_seconds=1_234)
    headers = policy.preflight_headers("https://a.com", request_method="POST")
    assert headers is not None
    assert headers["Access-Control-Max-Age"] == "1234"
    assert "POST" in headers["Access-Control-Allow-Methods"]


def test_a_preflight_is_rejected_for_a_disallowed_origin() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",))
    assert policy.preflight_headers("https://evil.com", request_method="GET") is None


def test_a_preflight_is_rejected_for_a_disallowed_method() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",), allow_methods=("GET",))
    assert policy.preflight_headers("https://a.com", request_method="DELETE") is None


def test_a_preflight_is_rejected_for_a_disallowed_header() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",), allow_headers=("X-Allowed",))
    assert (
        policy.preflight_headers(
            "https://a.com", request_method="GET", request_headers=["X-Forbidden"]
        )
        is None
    )


def test_simple_headers_never_need_to_be_declared() -> None:
    """``Content-Type`` y compañía son cabeceras que el navegador siempre
    puede enviar — exigir declararlas rompería peticiones perfectamente válidas."""
    policy = CorsPolicy(allow_origins=("https://a.com",))
    assert (
        policy.preflight_headers(
            "https://a.com", request_method="POST", request_headers=["Content-Type"]
        )
        is not None
    )


def test_a_wildcard_header_list_allows_anything() -> None:
    policy = CorsPolicy(allow_origins=("https://a.com",), allow_headers=("*",))
    assert policy.are_headers_allowed(["X-Whatever", "X-Custom"]) is True


# -- Versionado: parseo y orden -------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("v1", ApiVersion(1)),
        ("1", ApiVersion(1)),
        ("V2", ApiVersion(2)),
        ("v2.1", ApiVersion(2, 1)),
        ("3.0", ApiVersion(3, 0)),
        ("  v4  ", ApiVersion(4)),
    ],
)
def test_api_versions_parse_from_every_common_spelling(raw: str, expected: ApiVersion) -> None:
    assert ApiVersion.parse(raw) == expected


@pytest.mark.parametrize("raw", ["", "v", "abc", "1.2.3", "v-1", "1.x"])
def test_an_unparseable_version_raises(raw: str) -> None:
    with pytest.raises(ValueError):
        ApiVersion.parse(raw)


def test_api_versions_are_ordered() -> None:
    assert ApiVersion(1) < ApiVersion(2)
    assert ApiVersion(2, 1) > ApiVersion(2, 0)
    assert max(ApiVersion(1), ApiVersion(3), ApiVersion(2)) == ApiVersion(3)


def test_api_versions_render_without_a_trailing_zero_minor() -> None:
    assert str(ApiVersion(1)) == "v1"
    assert str(ApiVersion(1, 2)) == "v1.2"


# -- Versionado: negociación -------------------------------------------------------------------


def _negotiator(**overrides: object) -> ApiVersionNegotiator:
    defaults: dict[str, object] = {
        "supported": (ApiVersion(1), ApiVersion(2)),
        "default": ApiVersion(1),
    }
    defaults.update(overrides)
    return ApiVersionNegotiator(ApiVersioningPolicy(**defaults))  # type: ignore[arg-type]


def test_the_default_version_applies_when_the_client_asks_for_none() -> None:
    negotiation = _negotiator().negotiate(path="/orders")
    assert negotiation.version == ApiVersion(1)
    assert negotiation.is_default is True
    assert negotiation.strategy is None


def test_the_uri_strategy_reads_the_version_from_the_path() -> None:
    negotiation = _negotiator().negotiate(path="/api/v2/orders")
    assert negotiation.version == ApiVersion(2)
    assert negotiation.strategy is VersioningStrategy.URI


def test_the_uri_strategy_only_matches_a_whole_path_segment() -> None:
    """``/services/v2ray`` no declara la versión 2 — sin este anclaje, cualquier
    identificador que empiece por 'v' seguido de dígitos se confundiría."""
    negotiation = _negotiator().negotiate(path="/services/v2ray")
    assert negotiation.is_default is True


def test_the_header_strategy_reads_the_configured_header() -> None:
    negotiation = _negotiator().negotiate(path="/orders", headers={"X-API-Version": "2"})
    assert negotiation.version == ApiVersion(2)
    assert negotiation.strategy is VersioningStrategy.HEADER


def test_the_header_strategy_is_case_insensitive() -> None:
    negotiation = _negotiator().negotiate(path="/orders", headers={"x-api-version": "v2"})
    assert negotiation.version == ApiVersion(2)


def test_the_media_type_strategy_reads_the_accept_header() -> None:
    negotiation = _negotiator().negotiate(
        path="/orders", headers={"Accept": "application/vnd.teaf.v2+json"}
    )
    assert negotiation.version == ApiVersion(2)
    assert negotiation.strategy is VersioningStrategy.MEDIA_TYPE


def test_the_media_type_vendor_is_configurable() -> None:
    negotiator = _negotiator(media_type_vendor="torus")
    negotiation = negotiator.negotiate(
        path="/orders", headers={"Accept": "application/vnd.torus.v2+json"}
    )
    assert negotiation.version == ApiVersion(2)


def test_strategies_are_tried_in_the_configured_order() -> None:
    """Con URI antes que cabecera, la ruta manda aunque haya cabecera."""
    negotiation = _negotiator().negotiate(path="/api/v2/orders", headers={"X-API-Version": "1"})
    assert negotiation.version == ApiVersion(2)
    assert negotiation.strategy is VersioningStrategy.URI

    header_first = _negotiator(
        strategies=(VersioningStrategy.HEADER, VersioningStrategy.URI)
    ).negotiate(path="/api/v2/orders", headers={"X-API-Version": "1"})
    assert header_first.version == ApiVersion(1)


def test_a_disabled_strategy_is_ignored() -> None:
    negotiator = _negotiator(strategies=(VersioningStrategy.HEADER,))
    negotiation = negotiator.negotiate(path="/api/v2/orders")
    assert negotiation.is_default is True


# -- Versionado: versiones no soportadas y deprecación --------------------------------------------


def test_an_unsupported_version_is_rejected_in_strict_mode() -> None:
    with pytest.raises(UnsupportedApiVersionException) as exc_info:
        _negotiator().negotiate(path="/api/v9/orders")
    assert exc_info.value.requested == "9"
    assert exc_info.value.http_status == 400


def test_an_invalid_version_is_rejected_in_strict_mode() -> None:
    with pytest.raises(UnsupportedApiVersionException):
        _negotiator().negotiate(path="/orders", headers={"X-API-Version": "banana"})


def test_a_non_strict_policy_falls_back_to_the_default_version() -> None:
    negotiation = _negotiator(strict=False).negotiate(path="/api/v9/orders")
    assert negotiation.version == ApiVersion(1)
    assert negotiation.is_default is True
    assert negotiation.requested == "9"


def test_a_non_strict_policy_also_tolerates_an_unparseable_version() -> None:
    negotiation = _negotiator(strict=False).negotiate(
        path="/orders", headers={"X-API-Version": "banana"}
    )
    assert negotiation.version == ApiVersion(1)


def test_a_deprecated_version_carries_its_sunset_information() -> None:
    negotiator = _negotiator(deprecated={"v1": "Wed, 31 Dec 2026 23:59:59 GMT"})
    negotiation = negotiator.negotiate(path="/api/v1/orders")
    assert negotiation.deprecated is True
    assert negotiation.sunset == "Wed, 31 Dec 2026 23:59:59 GMT"

    headers = negotiator.response_headers(negotiation)
    assert headers["Deprecation"] == "true"
    assert headers["Sunset"] == "Wed, 31 Dec 2026 23:59:59 GMT"


def test_a_current_version_carries_no_deprecation_headers() -> None:
    negotiator = _negotiator(deprecated={"v1": "soon"})
    headers = negotiator.response_headers(negotiator.negotiate(path="/api/v2/orders"))
    assert headers == {"X-API-Version": "v2"}
