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
    OBSERVABILITY = "observability"
    #: Protección y gobernanza de APIs (Sprint 2.9, ADR-009) — rate limiting,
    #: quotas, CORS, versionado, validación, compresión, idempotencia y
    #: auditoría de API.
    API = "api"
