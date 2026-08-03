"""Enumeraciones del modelo de Feature Flags."""

from __future__ import annotations

from enum import Enum


class FeatureGroup(str, Enum):
    """Agrupación temática de un feature flag, para listarlos por área."""

    PLATFORM = "platform"
    SECURITY = "security"
    DATABASE = "database"
    AI = "ai"
    MCP = "mcp"
    EXPERIMENTAL = "experimental"
    INFRASTRUCTURE = "infrastructure"


class FeatureStatus(str, Enum):
    """Estado de activación de un feature flag."""

    ENABLED = "enabled"
    DISABLED = "disabled"
