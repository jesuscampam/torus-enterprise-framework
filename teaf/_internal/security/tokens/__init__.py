"""Emisión y verificación de tokens de sesión.

``jwt_provider.py`` implementa ``TokenProvider`` (contracts/security.py)
con JWT (access + refresh, revocación, rotación); ``api_key_provider.py``
implementa el almacén y las operaciones de API Keys (hash, expiración,
revocación, scopes, rotación) que consume
``identity_providers/api_key.py``.
"""

from __future__ import annotations
