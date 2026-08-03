"""``MODULE_TEMPLATES`` — plantillas internas por categoría de módulo.

Puramente datos: nombre, descripción y sugerencias de capacidades/servicios
por categoría — **ningún código de negocio** (ver Sprint 2.5, ítem 13).
Consumido por ``ModuleScaffolder`` (``scaffolder.py``) para generar el
esqueleto de un módulo nuevo.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.sdk.enums import ModuleCategory


@dataclass(frozen=True, slots=True)
class ModuleTemplate:
    """Sugerencias de estructura para un módulo de una categoría dada."""

    category: ModuleCategory
    name: str
    description: str
    suggested_capabilities: tuple[str, ...] = ()
    suggested_services: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de esta plantilla."""
        return {
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "suggestedCapabilities": list(self.suggested_capabilities),
            "suggestedServices": list(self.suggested_services),
        }


MODULE_TEMPLATES: dict[ModuleCategory, ModuleTemplate] = {
    ModuleCategory.GENERIC: ModuleTemplate(
        category=ModuleCategory.GENERIC,
        name="Generic Module",
        description="Módulo sin categoría específica — punto de partida mínimo.",
    ),
    ModuleCategory.DATABASE: ModuleTemplate(
        category=ModuleCategory.DATABASE,
        name="Database Module",
        description="Módulo que aporta acceso a una base de datos concreta.",
        suggested_capabilities=("database.query", "database.migrate"),
        suggested_services=("DatabaseProvider",),
    ),
    ModuleCategory.SECURITY: ModuleTemplate(
        category=ModuleCategory.SECURITY,
        name="Security Module",
        description="Módulo que aporta autenticación y/o autorización.",
        suggested_capabilities=("security.authenticate", "security.authorize"),
        suggested_services=("AuthenticationProvider", "AuthorizationProvider"),
    ),
    ModuleCategory.STORAGE: ModuleTemplate(
        category=ModuleCategory.STORAGE,
        name="Storage Module",
        description="Módulo que aporta almacenamiento de archivos/objetos.",
        suggested_capabilities=("storage.upload", "storage.download"),
        suggested_services=("StorageProvider",),
    ),
    ModuleCategory.INTEGRATION: ModuleTemplate(
        category=ModuleCategory.INTEGRATION,
        name="Integration Module",
        description="Módulo que integra TEAF con un sistema externo (SAP, Salesforce, Control-M).",
        suggested_capabilities=("integration.sync",),
    ),
    ModuleCategory.AI: ModuleTemplate(
        category=ModuleCategory.AI,
        name="AI Module",
        description="Módulo que aporta capacidades de generación de texto/embeddings.",
        suggested_capabilities=("ai.generate-text", "ai.generate-embedding"),
        suggested_services=("AIProvider",),
    ),
    ModuleCategory.MCP: ModuleTemplate(
        category=ModuleCategory.MCP,
        name="MCP Module",
        description="Módulo que expone capacidades del framework a un servidor MCP.",
        suggested_capabilities=("mcp.expose-tool",),
    ),
}


def get_template(category: ModuleCategory) -> ModuleTemplate:
    """Devuelve la plantilla de ``category`` (una entrada fija por cada una de las 7)."""
    return MODULE_TEMPLATES[category]
