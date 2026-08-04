"""Pruebas de ``ApiKeyProvider``: emisión, verificación, scopes, expiración/revocación/rotación."""

from __future__ import annotations

from datetime import timedelta

import pytest
from teaf._internal.security.exceptions import ApiKeyException
from teaf.security import ApiKeyProvider


def test_issue_returns_a_raw_key_and_a_record_that_only_stores_its_hash() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, record = provider.issue(principal_id="alice")
    assert raw_key.startswith("teaf_")
    assert record.principal_id == "alice"
    assert record.hashed_key != raw_key


def test_verify_returns_the_record_for_a_valid_key() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, record = provider.issue(principal_id="alice")
    verified = provider.verify(raw_key)
    assert verified.id == record.id


def test_verify_rejects_an_unknown_key() -> None:
    provider = ApiKeyProvider(secret="pepper")
    with pytest.raises(ApiKeyException):
        provider.verify("teaf_not-a-real-key")


def test_verify_rejects_a_revoked_key() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, record = provider.issue(principal_id="alice")
    provider.revoke(record.id)
    with pytest.raises(ApiKeyException):
        provider.verify(raw_key)


def test_verify_rejects_an_expired_key() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, _ = provider.issue(principal_id="alice", ttl=timedelta(seconds=-1))
    with pytest.raises(ApiKeyException):
        provider.verify(raw_key)


def test_verify_enforces_required_scope() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, _ = provider.issue(principal_id="alice", scopes=frozenset({"users:read"}))

    provider.verify(raw_key, required_scope="users:read")

    with pytest.raises(ApiKeyException):
        provider.verify(raw_key, required_scope="users:delete")


def test_revoke_of_unknown_key_raises() -> None:
    provider = ApiKeyProvider(secret="pepper")
    with pytest.raises(ApiKeyException):
        provider.revoke("not-a-real-id")


def test_rotate_invalidates_the_old_key_and_issues_a_new_one() -> None:
    provider = ApiKeyProvider(secret="pepper")
    raw_key, record = provider.issue(principal_id="alice", scopes=frozenset({"users:read"}))

    new_raw_key = provider.rotate(record.id)

    assert new_raw_key != raw_key
    with pytest.raises(ApiKeyException):
        provider.verify(raw_key)
    new_record = provider.verify(new_raw_key)
    assert new_record.scopes == frozenset({"users:read"})


def test_two_providers_with_different_secrets_do_not_accept_each_others_keys() -> None:
    provider_one = ApiKeyProvider(secret="pepper-one")
    provider_two = ApiKeyProvider(secret="pepper-two")
    raw_key, _ = provider_one.issue(principal_id="alice")
    with pytest.raises(ApiKeyException):
        provider_two.verify(raw_key)
