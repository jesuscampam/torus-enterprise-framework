"""Enumeraciones del Capability Model."""

from __future__ import annotations

from enum import Enum


class CapabilityCategory(str, Enum):
    """Categoría funcional de una capacidad, usada para agrupar y filtrar."""

    SYSTEM = "system"
    PLATFORM = "platform"
    DATABASE = "database"
    SECURITY = "security"
    STORAGE = "storage"
    AI = "ai"
    MCP = "mcp"
    NOTIFICATION = "notification"
    SCHEDULER = "scheduler"
    OBSERVABILITY = "observability"
    INTEGRATION = "integration"
    UTILITY = "utility"
    CUSTOM = "custom"


class CapabilityStatus(str, Enum):
    """Estado de registro de una capacidad."""

    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"


class CapabilityHealth(str, Enum):
    """Salud reportada de una capacidad. ``UNKNOWN`` por defecto — Sprint 2.4
    no conecta verificaciones de salud reales (ver Sprint 2.1, health checks
    estáticos, y el mismo principio aplicado aquí)."""

    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
