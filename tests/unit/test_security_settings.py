"""Pruebas de los campos de seguridad de ``Settings`` (Sprint 2.7, ADR-007)."""

from __future__ import annotations

from teaf._internal.config.settings import (
    ProductionSettings,
    Settings,
    TestingSettings,
)


def test_jwt_secret_defaults_to_none_not_a_predictable_value() -> None:
    settings = Settings()
    assert settings.jwt_secret is None


def test_jwt_defaults_match_the_recommended_values() -> None:
    settings = Settings()
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_access_token_ttl_seconds == 900
    assert settings.jwt_refresh_token_ttl_seconds == 1_209_600
    assert settings.jwt_clock_skew_seconds == 30


def test_api_key_defaults() -> None:
    settings = Settings()
    assert settings.api_key_header == "X-API-Key"
    assert settings.api_key_query_param == "api_key"
    assert settings.api_key_hash_secret is None


def test_ldap_settings_default_to_unconfigured() -> None:
    settings = Settings()
    assert settings.ldap_server_uri is None
    assert settings.ldap_base_dn is None
    assert settings.ldap_use_ssl is True


def test_azure_ad_settings_default_to_unconfigured() -> None:
    settings = Settings()
    assert settings.azure_ad_tenant is None
    assert settings.azure_ad_client_id is None
    assert settings.azure_ad_allowed_tenants is None


def test_multi_tenant_disabled_by_default() -> None:
    settings = Settings()
    assert settings.multi_tenant_enabled is False
    assert settings.default_tenant_id is None


def test_password_policy_defaults_to_argon2() -> None:
    settings = Settings()
    assert settings.password_hasher == "argon2"
    assert settings.argon2_time_cost == 3
    assert settings.argon2_memory_cost == 65536


def test_secret_rotation_disabled_by_default_but_enabled_in_production() -> None:
    assert Settings().secret_rotation_enabled is False
    assert ProductionSettings().secret_rotation_enabled is True


def test_security_headers_enabled_by_default() -> None:
    settings = Settings()
    assert settings.security_headers_enabled is True
    assert settings.security_frame_options == "DENY"


def test_testing_settings_reduces_password_hashing_cost() -> None:
    testing = TestingSettings()
    production = ProductionSettings()
    assert testing.argon2_time_cost < production.argon2_time_cost
    assert testing.argon2_memory_cost < production.argon2_memory_cost
    assert testing.bcrypt_rounds < production.bcrypt_rounds


def test_settings_fields_are_overridable_via_constructor() -> None:
    settings = Settings(jwt_secret="explicit-secret", jwt_algorithm="RS256")  # type: ignore[call-arg]
    assert settings.jwt_secret == "explicit-secret"
    assert settings.jwt_algorithm == "RS256"
