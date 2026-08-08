"""Criptografía de la plataforma de seguridad: hashing de contraseñas y firmas.

``password_hasher.py`` implementa ``PasswordHasher`` (Argon2id por defecto,
BCrypt como proveedor alternativo); ``crypto_provider.py`` implementa
``CryptoProvider`` (firmas HMAC-SHA256 con rotación de claves) — ver
``teaf/_internal/contracts/security.py`` para ambos contratos.
"""

from __future__ import annotations
