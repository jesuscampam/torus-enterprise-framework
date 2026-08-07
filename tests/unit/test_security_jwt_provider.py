"""Pruebas de ``JWTProvider`` (``JWTTokenProvider``): emisión, verificación, refresco/revocación."""

from __future__ import annotations

import asyncio
import time

import pytest
from teaf._internal.security.exceptions import (
    TokenException,
    TokenExpiredException,
    TokenRevokedException,
)
from teaf._internal.security.tokens.jwt_provider import InMemoryTokenRevocationStore
from teaf.security import Claims, Identity, JWTProvider


def _identity() -> Identity:
    claims = Claims(sub="alice", roles=frozenset({"admin"}))
    return Identity(id="alice", provider_id="jwt", claims=claims)


def test_issue_returns_access_and_refresh_tokens() -> None:
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    pair = asyncio.run(provider.issue(_identity()))
    assert pair.access_token
    assert pair.refresh_token
    assert pair.access_token != pair.refresh_token
    assert pair.token_type == "Bearer"


def test_verify_returns_the_identity_encoded_in_the_access_token() -> None:
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    pair = asyncio.run(provider.issue(_identity()))
    identity = asyncio.run(provider.verify(pair.access_token))
    assert identity.id == "alice"
    assert identity.claims.roles == frozenset({"admin"})


def test_verify_rejects_a_refresh_token_presented_as_access_token() -> None:
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    pair = asyncio.run(provider.issue(_identity()))
    with pytest.raises(TokenException):
        asyncio.run(provider.verify(pair.refresh_token))


def test_verify_rejects_a_token_signed_with_a_different_secret() -> None:
    provider = JWTProvider(secret="secret-one-with-at-least-32-bytes!!!!")
    other_provider = JWTProvider(secret="secret-two-with-at-least-32-bytes!!!!")
    pair = asyncio.run(provider.issue(_identity()))
    with pytest.raises(TokenException):
        asyncio.run(other_provider.verify(pair.access_token))


def test_verify_raises_token_expired_after_ttl_with_zero_clock_skew() -> None:
    provider = JWTProvider(
        secret="test-secret-with-at-least-32-bytes!!",
        access_token_ttl_seconds=1,
        clock_skew_seconds=0,
    )
    pair = asyncio.run(provider.issue(_identity()))
    time.sleep(2)
    with pytest.raises(TokenExpiredException):
        asyncio.run(provider.verify(pair.access_token))


def test_clock_skew_tolerates_expiration_within_the_leeway() -> None:
    provider = JWTProvider(
        secret="test-secret-with-at-least-32-bytes!!",
        access_token_ttl_seconds=1,
        clock_skew_seconds=30,
    )
    pair = asyncio.run(provider.issue(_identity()))
    time.sleep(2)
    identity = asyncio.run(provider.verify(pair.access_token))
    assert identity.id == "alice"


def test_refresh_issues_a_new_pair_and_revokes_the_used_refresh_token() -> None:
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    pair = asyncio.run(provider.issue(_identity()))

    new_pair = asyncio.run(provider.refresh(pair.refresh_token))
    assert new_pair.access_token != pair.access_token

    with pytest.raises(TokenRevokedException):
        asyncio.run(provider.refresh(pair.refresh_token))


def test_revoke_makes_a_valid_access_token_fail_verification() -> None:
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!")
    pair = asyncio.run(provider.issue(_identity()))

    asyncio.run(provider.revoke(pair.access_token))

    with pytest.raises(TokenRevokedException):
        asyncio.run(provider.verify(pair.access_token))


def test_revoke_of_an_already_expired_token_does_not_raise() -> None:
    provider = JWTProvider(
        secret="test-secret-with-at-least-32-bytes!!",
        access_token_ttl_seconds=1,
        clock_skew_seconds=0,
    )
    pair = asyncio.run(provider.issue(_identity()))
    time.sleep(2)
    asyncio.run(provider.revoke(pair.access_token))  # no debe lanzar


def test_custom_revocation_store_is_used_instead_of_the_default() -> None:
    store = InMemoryTokenRevocationStore()
    provider = JWTProvider(secret="test-secret-with-at-least-32-bytes!!", revocation_store=store)
    pair = asyncio.run(provider.issue(_identity()))

    asyncio.run(provider.revoke(pair.access_token))

    assert len(store._revoked) == 1  # type: ignore[attr-defined]
