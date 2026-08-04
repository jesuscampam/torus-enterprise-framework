"""Implementación de ``CryptoProvider`` (ver contracts/security.py).

Firmas HMAC-SHA256 con soporte de rotación de claves: ``rotate_keys()``
promueve una clave nueva a activa conservando la anterior únicamente para
verificar firmas ya emitidas — nunca para firmar contenido nuevo. Distinto
de ``PasswordHasher``: este proveedor es para firmar/verificar datos
arbitrarios (p. ej. un ``state`` de OAuth2, un token de un solo uso), no
para contraseñas de usuario.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

from teaf._internal.contracts.security import CryptoProvider


class HmacCryptoProvider(CryptoProvider):
    """Firma/verifica con HMAC-SHA256 sobre una o más claves secretas."""

    def __init__(self, *, secret_keys: tuple[bytes, ...]) -> None:
        """``secret_keys[0]`` es la clave activa (usada para firmar); el resto solo
        se usan para verificar firmas emitidas antes de la rotación más reciente."""
        if not secret_keys:
            raise ValueError("HmacCryptoProvider requiere al menos una clave.")
        self._keys: list[bytes] = list(secret_keys)

    @property
    def active_key(self) -> bytes:
        """La clave usada para firmar contenido nuevo."""
        return self._keys[0]

    def sign(self, data: bytes) -> bytes:
        """Firma ``data`` con la clave activa."""
        return hmac.new(self.active_key, data, hashlib.sha256).digest()

    def verify_signature(self, data: bytes, signature: bytes) -> bool:
        """``True`` si ``signature`` es válida para ``data`` con la clave activa o una anterior."""
        return any(
            hmac.compare_digest(hmac.new(key, data, hashlib.sha256).digest(), signature)
            for key in self._keys
        )

    def generate_key(self) -> bytes:
        """Genera 32 bytes criptográficamente seguros (``secrets.token_bytes``)."""
        return secrets.token_bytes(32)

    def rotate_keys(self) -> None:
        """Promueve una clave nueva a activa; conserva únicamente la anterior para verificar."""
        self._keys = [self.generate_key(), self._keys[0]]
