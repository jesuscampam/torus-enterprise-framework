"""``secrets/`` — gestión de secretos (v1.0-beta MVP).

Desacoplamiento de implementación: env vars hoy, Vault/Azure Key Vault en v1.0.1.
"""

from __future__ import annotations

from teaf._internal.secrets.provider import SecretProvider
from teaf._internal.secrets.providers.env_vars import EnvVarsProvider

__all__ = [
    "SecretProvider",
    "EnvVarsProvider",
]
