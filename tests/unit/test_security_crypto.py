"""Pruebas de ``PasswordHasher`` (Argon2id/BCrypt) y ``CryptoProvider`` (HMAC)."""

from __future__ import annotations

import pytest
from teaf.security import Argon2PasswordHasher, BcryptPasswordHasher, HmacCryptoProvider

# Costes reducidos a propósito — mismo criterio que ``TestingSettings``
# (ver teaf/_internal/config/settings.py): no ralentizar la suite.
_FAST_ARGON2_KWARGS = {"time_cost": 1, "memory_cost": 8, "parallelism": 1}


@pytest.mark.parametrize(
    "hasher",
    [Argon2PasswordHasher(**_FAST_ARGON2_KWARGS), BcryptPasswordHasher(rounds=4)],
)
def test_verify_succeeds_for_the_password_that_was_hashed(hasher: object) -> None:
    hashed = hasher.hash("correct horse battery staple")  # type: ignore[attr-defined]
    assert hasher.verify("correct horse battery staple", hashed) is True  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "hasher",
    [Argon2PasswordHasher(**_FAST_ARGON2_KWARGS), BcryptPasswordHasher(rounds=4)],
)
def test_verify_fails_for_the_wrong_password(hasher: object) -> None:
    hashed = hasher.hash("correct horse battery staple")  # type: ignore[attr-defined]
    assert hasher.verify("wrong password", hashed) is False  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "hasher",
    [Argon2PasswordHasher(**_FAST_ARGON2_KWARGS), BcryptPasswordHasher(rounds=4)],
)
def test_verify_never_raises_on_malformed_hash(hasher: object) -> None:
    assert hasher.verify("anything", "not-a-real-hash") is False  # type: ignore[attr-defined]


def test_argon2_needs_rehash_is_false_for_matching_cost_parameters() -> None:
    hasher = Argon2PasswordHasher(**_FAST_ARGON2_KWARGS)
    hashed = hasher.hash("password")
    assert hasher.needs_rehash(hashed) is False


def test_argon2_needs_rehash_is_true_when_cost_parameters_increase() -> None:
    weak_hasher = Argon2PasswordHasher(**_FAST_ARGON2_KWARGS)
    hashed = weak_hasher.hash("password")
    strong_hasher = Argon2PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
    assert strong_hasher.needs_rehash(hashed) is True


def test_bcrypt_needs_rehash_is_true_when_rounds_increase() -> None:
    weak_hasher = BcryptPasswordHasher(rounds=4)
    hashed = weak_hasher.hash("password")
    strong_hasher = BcryptPasswordHasher(rounds=12)
    assert strong_hasher.needs_rehash(hashed) is True


def test_hmac_crypto_provider_requires_at_least_one_key() -> None:
    with pytest.raises(ValueError):
        HmacCryptoProvider(secret_keys=())


def test_hmac_sign_and_verify_round_trip() -> None:
    provider = HmacCryptoProvider(secret_keys=(b"secret-key",))
    signature = provider.sign(b"payload")
    assert provider.verify_signature(b"payload", signature) is True


def test_hmac_verify_fails_for_tampered_data() -> None:
    provider = HmacCryptoProvider(secret_keys=(b"secret-key",))
    signature = provider.sign(b"payload")
    assert provider.verify_signature(b"tampered", signature) is False


def test_hmac_generate_key_returns_32_random_bytes() -> None:
    provider = HmacCryptoProvider(secret_keys=(b"secret-key",))
    key_one = provider.generate_key()
    key_two = provider.generate_key()
    assert len(key_one) == 32
    assert key_one != key_two


def test_hmac_rotate_keys_keeps_verifying_old_signatures() -> None:
    provider = HmacCryptoProvider(secret_keys=(b"key-v1",))
    old_signature = provider.sign(b"payload")

    provider.rotate_keys()
    new_signature = provider.sign(b"payload")

    assert new_signature != old_signature
    assert provider.verify_signature(b"payload", old_signature) is True
    assert provider.verify_signature(b"payload", new_signature) is True


def test_hmac_rotate_keys_twice_drops_signatures_from_two_rotations_ago() -> None:
    provider = HmacCryptoProvider(secret_keys=(b"key-v1",))
    oldest_signature = provider.sign(b"payload")

    provider.rotate_keys()
    provider.rotate_keys()

    assert provider.verify_signature(b"payload", oldest_signature) is False
