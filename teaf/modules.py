"""``teaf.modules`` — construir y describir módulos TEAF.

Fachada sobre el Module SDK (``teaf/_internal/sdk/``, Sprint 2.5): un desarrollador
de módulos solo necesita los símbolos de este archivo (reexportados también
desde ``teaf`` directamente) — nunca importa ``teaf._internal.sdk.*`` a mano.

``Module`` es un alias de ``ModuleBase`` — el mismo objeto, con un nombre
más corto para quien solo quiere heredar de él (``class MiModulo(teaf.Module)``);
``ModuleBase`` sigue disponible con su nombre completo para quien prefiera
la nomenclatura explícita del SDK. No son dos clases distintas.
"""

from __future__ import annotations

from teaf._internal.core.registry import ModuleRegistry
from teaf._internal.sdk.builder import ModuleBuilder
from teaf._internal.sdk.context import ModuleContext
from teaf._internal.sdk.enums import ModuleCategory
from teaf._internal.sdk.manifest import ModuleManifest
from teaf._internal.sdk.module_base import ModuleBase

#: Alias corto de ``ModuleBase`` — ver docstring del módulo.
Module = ModuleBase

__all__ = [
    "Module",
    "ModuleBase",
    "ModuleBuilder",
    "ModuleCategory",
    "ModuleContext",
    "ModuleManifest",
    "ModuleRegistry",
]
