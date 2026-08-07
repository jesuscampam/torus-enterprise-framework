"""Pruebas de la política de longitud mínima del secreto JWT (Sprint 3.0).

Sprint 2.9.2 dejó constancia de que TEAF aceptaba `"test-secret"` (11 bytes)
para firmar HS256 sin decir nada. Estas pruebas fijan que ya no, en los dos
puntos por los que un secreto entra al framework —la configuración y la
construcción directa del proveedor— y que el mínimo **se deriva del
algoritmo** en vez de ser un número elegido a ojo.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from teaf._internal.config.settings import Settings
from teaf._internal.core.exceptions import ConfigurationException
from teaf._internal.security.tokens.jwt_policy import (
    describe_secret_violation,
    minimum_secret_bytes,
)
from teaf._internal.security.tokens.jwt_provider import JWTTokenProvider

#: 32 bytes exactos — el mínimo de HS256.
SECRETO_VALIDO = "a" * 32


# -- La política, aislada ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("algoritmo", "esperado"),
    [("HS256", 32), ("HS384", 48), ("HS512", 64), ("hs256", 32), ("  HS256  ", 32)],
)
def test_el_minimo_se_deriva_del_algoritmo(algoritmo: str, esperado: int) -> None:
    """RFC 7518 §3.2: la clave HMAC mide al menos lo que la salida del hash."""
    assert minimum_secret_bytes(algoritmo) == esperado


@pytest.mark.parametrize("algoritmo", ["RS256", "ES256", "PS512", "EdDSA"])
def test_los_algoritmos_asimetricos_no_tienen_minimo(algoritmo: str) -> None:
    """Ahí el 'secreto' es una clave PEM: medir sus bytes no diría nada."""
    assert minimum_secret_bytes(algoritmo) == 0
    assert describe_secret_violation("corto", algoritmo) is None


def test_un_secreto_suficiente_no_produce_violacion() -> None:
    assert describe_secret_violation(SECRETO_VALIDO, "HS256") is None


def test_un_secreto_corto_produce_violacion() -> None:
    violacion = describe_secret_violation("corto", "HS256")
    assert violacion is not None
    assert "5 bytes" in violacion
    assert "mínimo 32" in violacion


def test_el_mensaje_nunca_revela_el_secreto() -> None:
    """Acabaría en un log o en una traza."""
    secreto = "clave-supersecreta-de-produccion"[:20]
    violacion = describe_secret_violation(secreto, "HS256")
    assert violacion is not None
    assert secreto not in violacion


def test_el_mensaje_nombra_algoritmo_y_estandar() -> None:
    violacion = describe_secret_violation("x", "HS512")
    assert violacion is not None
    assert "HS512" in violacion
    assert "RFC 7518" in violacion


def test_secreto_ausente_no_valida_nada() -> None:
    """``None`` significa «JWT sin configurar», no «secreto vacío»."""
    assert describe_secret_violation(None, "HS256") is None


def test_la_longitud_se_mide_en_bytes_no_en_caracteres() -> None:
    """31 caracteres multibyte superan los 32 bytes; contar caracteres se equivocaría."""
    assert describe_secret_violation("ñ" * 31, "HS256") is None
    assert describe_secret_violation("a" * 31, "HS256") is not None


# -- Punto 1: la configuración -------------------------------------------------------------


def test_la_configuracion_rechaza_un_secreto_corto() -> None:
    with pytest.raises(ValidationError) as error:
        Settings(jwt_secret="demasiado-corto")
    assert "RFC 7518" in str(error.value)


def test_la_configuracion_acepta_un_secreto_conforme() -> None:
    assert Settings(jwt_secret=SECRETO_VALIDO).jwt_secret == SECRETO_VALIDO


def test_la_configuracion_sin_jwt_sigue_siendo_valida() -> None:
    """Una aplicación que no usa JWT no tiene por qué declarar un secreto."""
    assert Settings().jwt_secret is None


def test_la_configuracion_exige_mas_para_hs512() -> None:
    """El mínimo sigue al algoritmo también en la configuración."""
    with pytest.raises(ValidationError):
        Settings(jwt_secret=SECRETO_VALIDO, jwt_algorithm="HS512")
    assert Settings(jwt_secret="b" * 64, jwt_algorithm="HS512").jwt_algorithm == "HS512"


# -- Punto 2: el proveedor -----------------------------------------------------------------


def test_el_proveedor_rechaza_un_secreto_corto_al_construirse() -> None:
    """Falla al construir, no al firmar: es un error de despliegue."""
    with pytest.raises(ConfigurationException) as error:
        JWTTokenProvider(secret="corto")
    assert "RFC 7518" in str(error.value)


def test_el_proveedor_acepta_un_secreto_conforme() -> None:
    assert JWTTokenProvider(secret=SECRETO_VALIDO) is not None


def test_el_proveedor_no_valida_longitud_con_algoritmos_asimetricos() -> None:
    """Una clave PEM no se mide con esta regla."""
    assert JWTTokenProvider(secret="-----BEGIN PUBLIC KEY-----", algorithm="RS256") is not None
