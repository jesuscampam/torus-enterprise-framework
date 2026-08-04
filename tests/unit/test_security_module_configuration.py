"""Pruebas de ``SecurityConfiguration``/``SecurityHealth`` (Module SDK, Sprint 2.7)."""

from __future__ import annotations

import asyncio

from teaf._internal.modules.security.configuration import SecurityConfiguration
from teaf._internal.modules.security.health import SecurityHealth
from teaf._internal.runtime.capabilities.enums import CapabilityHealth
from teaf.security import AnonymousIdentityProvider, IdentityProviderRegistry


def test_default_jwt_secret_is_random_and_unique_per_instance() -> None:
    first = SecurityConfiguration()
    second = SecurityConfiguration()
    assert first.jwt_secret != second.jwt_secret
    assert len(first.jwt_secret) > 0


def test_defaults_match_the_documented_recommendations() -> None:
    configuration = SecurityConfiguration()
    assert configuration.jwt_algorithm == "HS256"
    assert configuration.access_token_ttl_seconds == 900
    assert configuration.refresh_token_ttl_seconds == 1_209_600
    assert configuration.password_hasher == "argon2"
    assert configuration.roles == {}


def test_from_mapping_uses_explicit_jwt_secret_when_provided() -> None:
    configuration = SecurityConfiguration.from_mapping({"jwt_secret": "explicit-secret"})
    assert configuration.jwt_secret == "explicit-secret"


def test_from_mapping_generates_a_random_secret_when_absent() -> None:
    configuration = SecurityConfiguration.from_mapping({})
    assert configuration.jwt_secret is not None
    assert len(configuration.jwt_secret) > 0


def test_from_mapping_coerces_string_ttl_to_int() -> None:
    configuration = SecurityConfiguration.from_mapping({"access_token_ttl_seconds": "1200"})
    assert configuration.access_token_ttl_seconds == 1200
    assert isinstance(configuration.access_token_ttl_seconds, int)


def test_from_mapping_ignores_absent_keys_and_uses_defaults() -> None:
    configuration = SecurityConfiguration.from_mapping({"jwt_algorithm": "RS256"})
    assert configuration.jwt_algorithm == "RS256"
    assert configuration.jwt_issuer == "teaf"


def test_health_starts_unknown_before_refresh() -> None:
    registry = IdentityProviderRegistry([AnonymousIdentityProvider()])
    health = SecurityHealth(registry)
    assert health.check() is CapabilityHealth.UNKNOWN


def test_health_becomes_healthy_when_at_least_one_provider_is_registered() -> None:
    registry = IdentityProviderRegistry([AnonymousIdentityProvider()])
    health = SecurityHealth(registry)
    result = asyncio.run(health.refresh())
    assert result is CapabilityHealth.HEALTHY
    assert health.check() is CapabilityHealth.HEALTHY


def test_health_becomes_degraded_when_no_provider_is_registered() -> None:
    registry = IdentityProviderRegistry([])
    health = SecurityHealth(registry)
    result = asyncio.run(health.refresh())
    assert result is CapabilityHealth.DEGRADED
