"""Enumeraciones del Module SDK."""

from __future__ import annotations

from enum import Enum


class ModuleCategory(str, Enum):
    """Categoría de un módulo — también el eje de ``MODULE_TEMPLATES`` (``templates.py``)."""

    GENERIC = "generic"
    DATABASE = "database"
    SECURITY = "security"
    STORAGE = "storage"
    INTEGRATION = "integration"
    AI = "ai"
    MCP = "mcp"
