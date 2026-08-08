"""Pruebas unitarias de ``RequestValidator`` y de la compresión (Sprint 2.9)."""

from __future__ import annotations

import gzip

import pytest
from teaf._internal.api.compression import providers as compression_module
from teaf.api import (
    BrotliCompressionProvider,
    CompressionAlgorithm,
    CompressionNegotiator,
    CompressionPolicy,
    GzipCompressionProvider,
    InvalidRequestException,
    RequestTooLargeException,
    RequestValidationPolicy,
    RequestValidator,
    ResponseTooLargeException,
    UnsupportedContentTypeException,
    parse_accept_encoding,
)

# -- Validación: tamaño ---------------------------------------------------------------


def test_a_request_under_the_limit_passes() -> None:
    validator = RequestValidator(RequestValidationPolicy(max_request_bytes=1_000))
    validator.validate_request(method="POST", content_length=999)


def test_a_request_over_the_limit_is_rejected_with_413() -> None:
    validator = RequestValidator(RequestValidationPolicy(max_request_bytes=1_000))
    with pytest.raises(RequestTooLargeException) as exc_info:
        validator.validate_request(method="POST", content_length=1_001)
    assert exc_info.value.http_status == 413


def test_the_size_is_read_from_the_content_length_header_when_not_given() -> None:
    validator = RequestValidator(RequestValidationPolicy(max_request_bytes=100))
    with pytest.raises(RequestTooLargeException):
        validator.validate_request(method="POST", headers={"Content-Length": "500"})


def test_a_malformed_content_length_is_treated_as_empty() -> None:
    """Un ``Content-Length`` no numérico no debe tumbar la petición aquí: el
    servidor ASGI ya rechaza los marcos HTTP inválidos antes de llegar."""
    validator = RequestValidator(RequestValidationPolicy(max_request_bytes=10))
    validator.validate_request(method="POST", headers={"Content-Length": "abc"})


def test_a_response_over_the_limit_is_rejected_as_a_server_error() -> None:
    validator = RequestValidator(RequestValidationPolicy(max_response_bytes=100))
    with pytest.raises(ResponseTooLargeException) as exc_info:
        validator.validate_response(content_length=101)
    assert exc_info.value.http_status == 500


# -- Validación: tipo de contenido -------------------------------------------------------


def test_an_allowed_content_type_passes_ignoring_its_parameters() -> None:
    validator = RequestValidator(
        RequestValidationPolicy(allowed_content_types=("application/json",))
    )
    validator.validate_request(
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8", "Content-Length": "10"},
    )


def test_a_forbidden_content_type_is_rejected_with_415() -> None:
    validator = RequestValidator(
        RequestValidationPolicy(allowed_content_types=("application/json",))
    )
    with pytest.raises(UnsupportedContentTypeException) as exc_info:
        validator.validate_request(
            method="POST", headers={"Content-Type": "text/xml", "Content-Length": "10"}
        )
    assert exc_info.value.http_status == 415


def test_a_missing_content_type_is_rejected_when_there_is_an_allow_list() -> None:
    validator = RequestValidator(
        RequestValidationPolicy(allowed_content_types=("application/json",))
    )
    with pytest.raises(UnsupportedContentTypeException):
        validator.validate_request(method="POST", headers={"Content-Length": "10"})


@pytest.mark.parametrize("method", ["GET", "HEAD", "DELETE", "OPTIONS"])
def test_bodyless_methods_never_need_a_content_type(method: str) -> None:
    validator = RequestValidator(
        RequestValidationPolicy(allowed_content_types=("application/json",))
    )
    validator.validate_request(method=method)


def test_an_empty_body_never_needs_a_content_type() -> None:
    validator = RequestValidator(
        RequestValidationPolicy(allowed_content_types=("application/json",))
    )
    validator.validate_request(method="POST", content_length=0)


def test_no_allow_list_means_any_content_type_is_fine() -> None:
    RequestValidator().validate_request(
        method="POST", headers={"Content-Type": "application/octet-stream"}, content_length=5
    )


# -- Validación: cabeceras, agente y URL ----------------------------------------------------


def test_a_missing_required_header_is_rejected_with_400() -> None:
    validator = RequestValidator(RequestValidationPolicy(required_headers=("X-Request-Id",)))
    with pytest.raises(InvalidRequestException) as exc_info:
        validator.validate_request(method="GET")
    assert exc_info.value.http_status == 400


def test_required_headers_are_matched_case_insensitively() -> None:
    validator = RequestValidator(RequestValidationPolicy(required_headers=("X-Request-Id",)))
    validator.validate_request(method="GET", headers={"x-request-id": "abc"})


def test_a_blocked_user_agent_is_rejected() -> None:
    validator = RequestValidator(RequestValidationPolicy(blocked_user_agents=("BadBot",)))
    with pytest.raises(InvalidRequestException):
        validator.validate_request(method="GET", headers={"User-Agent": "Mozilla BadBot/2.0"})


def test_an_allow_list_of_user_agents_rejects_everything_else() -> None:
    validator = RequestValidator(RequestValidationPolicy(allowed_user_agents=("TorusClient",)))
    validator.validate_request(method="GET", headers={"User-Agent": "TorusClient/1.0"})
    with pytest.raises(InvalidRequestException):
        validator.validate_request(method="GET", headers={"User-Agent": "curl/8.0"})


def test_a_missing_user_agent_is_only_rejected_when_required() -> None:
    RequestValidator().validate_request(method="GET")
    with pytest.raises(InvalidRequestException):
        RequestValidator(RequestValidationPolicy(require_user_agent=True)).validate_request(
            method="GET"
        )


def test_an_overlong_url_is_rejected() -> None:
    validator = RequestValidator(RequestValidationPolicy(max_url_length=50))
    with pytest.raises(InvalidRequestException):
        validator.validate_request(method="GET", url="/" + "a" * 100)


# -- Compresión: proveedores ------------------------------------------------------------------


def test_gzip_is_always_available_and_produces_valid_gzip() -> None:
    provider = GzipCompressionProvider()
    payload = b"hola " * 500
    assert provider.available is True
    assert provider.algorithm is CompressionAlgorithm.GZIP
    assert gzip.decompress(provider.compress(payload)) == payload


def test_gzip_output_is_deterministic() -> None:
    """``mtime=0``: sin ello dos ejecuciones del mismo contenido producirían
    bytes distintos y ninguna caché podría compararlos."""
    provider = GzipCompressionProvider()
    assert provider.compress(b"x" * 1_000) == provider.compress(b"x" * 1_000)


def test_brotli_reports_its_availability_honestly() -> None:
    provider = BrotliCompressionProvider()
    assert provider.algorithm is CompressionAlgorithm.BROTLI
    assert provider.available is (compression_module._brotli is not None)


def test_brotli_fails_loudly_when_the_optional_package_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compression_module, "_brotli", None)
    provider = BrotliCompressionProvider()
    assert provider.available is False
    with pytest.raises(RuntimeError, match="Brotli no está disponible"):
        provider.compress(b"x" * 100)


def test_brotli_compresses_through_whichever_package_is_installed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Se sustituye el módulo por un doble para probar la ruta de compresión
    sin depender de que ``brotli`` esté instalado en este intérprete."""

    class _FakeBrotli:
        @staticmethod
        def compress(data: bytes, quality: int = 11) -> bytes:
            return b"BR" + data[:4]

    monkeypatch.setattr(compression_module, "_brotli", _FakeBrotli)
    provider = BrotliCompressionProvider(quality=4)
    assert provider.available is True
    assert provider.compress(b"hola mundo") == b"BRhola"


# -- Compresión: negociación --------------------------------------------------------------------


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("gzip", ("gzip",)),
        ("br, gzip", ("br", "gzip")),
        ("gzip;q=0.5, br;q=1.0", ("br", "gzip")),
        ("gzip;q=0, br", ("br",)),
        ("", ()),
        ("gzip;q=bad", ("gzip",)),
    ],
)
def test_accept_encoding_is_parsed_by_client_preference(
    header: str, expected: tuple[str, ...]
) -> None:
    assert parse_accept_encoding(header) == expected


def _negotiator(**policy: object) -> CompressionNegotiator:
    return CompressionNegotiator(
        [GzipCompressionProvider()],
        policy=CompressionPolicy(minimum_size_bytes=100, **policy),  # type: ignore[arg-type]
    )


def test_a_large_compressible_response_gets_a_provider() -> None:
    provider = _negotiator().select(
        accept_encoding="gzip", content_type="application/json", content_length=5_000
    )
    assert provider is not None and provider.algorithm is CompressionAlgorithm.GZIP


def test_a_response_below_the_threshold_is_not_compressed() -> None:
    assert (
        _negotiator().select(
            accept_encoding="gzip", content_type="application/json", content_length=50
        )
        is None
    )


def test_an_incompressible_content_type_is_skipped() -> None:
    """Comprimir un JPEG gasta CPU para no ahorrar nada — y a veces agranda."""
    assert (
        _negotiator().select(
            accept_encoding="gzip", content_type="image/jpeg", content_length=5_000
        )
        is None
    )


def test_a_response_without_content_type_is_not_compressed() -> None:
    assert (
        _negotiator().select(accept_encoding="gzip", content_type=None, content_length=5_000)
        is None
    )


def test_a_client_that_accepts_nothing_gets_no_compression() -> None:
    assert (
        _negotiator().select(
            accept_encoding="", content_type="application/json", content_length=5_000
        )
        is None
    )


def test_a_client_that_only_accepts_brotli_gets_nothing_from_a_gzip_only_server() -> None:
    assert (
        _negotiator().select(
            accept_encoding="br", content_type="application/json", content_length=5_000
        )
        is None
    )


def test_the_wildcard_encoding_takes_the_server_preference() -> None:
    provider = _negotiator().select(
        accept_encoding="*", content_type="application/json", content_length=5_000
    )
    assert provider is not None and provider.algorithm is CompressionAlgorithm.GZIP


def test_a_disabled_policy_never_compresses() -> None:
    negotiator = _negotiator(enabled=False)
    assert (
        negotiator.select(
            accept_encoding="gzip", content_type="application/json", content_length=5_000
        )
        is None
    )


def test_unavailable_providers_are_dropped_at_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compression_module, "_brotli", None)
    negotiator = CompressionNegotiator([BrotliCompressionProvider(), GzipCompressionProvider()])
    assert [p.algorithm for p in negotiator.providers] == [CompressionAlgorithm.GZIP]


def test_a_negotiator_without_providers_never_compresses() -> None:
    negotiator = CompressionNegotiator([])
    assert (
        negotiator.select(
            accept_encoding="gzip", content_type="application/json", content_length=5_000
        )
        is None
    )


@pytest.mark.parametrize(
    ("content_type", "compressible"),
    [
        ("text/html", True),
        ("text/plain; charset=utf-8", True),
        ("application/json", True),
        ("application/xml", True),
        ("image/svg+xml", True),
        ("image/png", False),
        ("application/zip", False),
        ("application/octet-stream", False),
    ],
)
def test_the_compressible_type_list_covers_the_usual_cases(
    content_type: str, compressible: bool
) -> None:
    assert CompressionPolicy().is_compressible(content_type) is compressible
