"""``ModuleDescriptor`` — metadata de identidad de un módulo, en tiempo de autoría.

Deliberadamente **homónimo** de ``backend.core.registry.ModuleDescriptor``
(el descriptor en tiempo de ejecución del ``ModuleRegistry``, Sprint 2.2) —
son dos capas distintas a propósito: este describe un módulo **antes** de
que exista un ``Runtime`` (es la "Metadata" de un ``ModuleManifest``, ver
``manifest.py``); el de Core describe un módulo **ya registrado**. Nunca se
usan indistintamente — donde ambos deban coexistir (ver
``module_base.py``), se importan con alias explícitos
(``from backend.core.registry import ModuleDescriptor as CoreModuleDescriptor``).
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.sdk.enums import ModuleCategory


@dataclass(frozen=True, slots=True)
class ModuleDescriptor:
    """Identidad de un módulo: quién es, qué versión, a qué categoría pertenece."""

    id: str
    name: str
    display_name: str
    version: str
    description: str = ""
    author: str | None = None
    category: ModuleCategory = ModuleCategory.GENERIC
    tags: tuple[str, ...] = ()
    documentation: str | None = None
    experimental: bool = False
    deprecated: bool = False

    def as_dict(self) -> dict[str, object]:
        """Representación serializable (JSON) de este descriptor."""
        return {
            "id": self.id,
            "name": self.name,
            "displayName": self.display_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "tags": list(self.tags),
            "documentation": self.documentation,
            "experimental": self.experimental,
            "deprecated": self.deprecated,
        }
