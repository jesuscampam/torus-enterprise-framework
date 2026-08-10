"""Proveedores de secretos — implementaciones concretas de ``SecretProvider``."""

from __future__ import annotations

from teaf._internal.secrets.providers.env_vars import EnvVarsProvider

__all__ = ["EnvVarsProvider"]
