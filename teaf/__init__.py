"""``teaf`` — la única API pública de TORUS Enterprise Application Framework.

Desde este Sprint (2.5.1, Public SDK & Packaging), un consumidor externo de
TEAF nunca importa ``teaf._internal.*`` directamente — solo ``from teaf import ...``.
``teaf/_internal/`` (``core``, ``config``, ``runtime``, ``sdk``, ``contracts``,
``providers``, ``modules``, ...) es la implementación privada detrás de
esta fachada; puede reorganizarse internamente entre Sprints sin romper a
ningún consumidor de ``teaf`` mientras el contrato de este archivo se
mantenga (ver docs/public-api/VERSIONING.md, ``PUBLIC_API_VERSION``).

Cada símbolo exportado aquí vive, en realidad, en una fachada especializada
bajo ``teaf/`` (``application.py``, ``runtime.py``, ``modules.py``,
``services.py``, ``events.py``, ``configuration.py``, ``capabilities.py``,
``health.py``, ``version.py``) — ver docs/public-api/PACKAGE-STRUCTURE.md
para qué vive en cada una. Este archivo solo agrega, nunca implementa.

Superficie pública: los catorce símbolos pedidos explícitamente
(``Application``, ``Runtime``, ``Module``, ``ModuleBase``, ``ModuleBuilder``,
``ModuleContext``, ``ModuleManifest``, ``ServiceContainer``, ``EventBus``,
``CapabilityRegistry``, ``ModuleRegistry``, ``Health``, ``Configuration``,
``Version``) más un puñado de enums/dataclasses *compañeros*, sin los
cuales los símbolos principales no se podrían usar en la práctica sin
recurrir a ``teaf._internal.*`` (``ModuleCategory``/``CapabilityCategory`` para
categorizar; ``Lifetime`` para declarar el ciclo de vida de un servicio;
``Event`` para publicar en el ``EventBus``; ``get_configuration`` como
función homóloga de ``Configuration``). Nada más se exporta — no hay
importaciones implícitas ni reexportaciones accidentales de símbolos
internos.
"""

from __future__ import annotations

from teaf.application import Application
from teaf.capabilities import CapabilityCategory, CapabilityRegistry
from teaf.configuration import Configuration, get_configuration
from teaf.events import Event, EventBus
from teaf.health import Health
from teaf.modules import (
    Module,
    ModuleBase,
    ModuleBuilder,
    ModuleCategory,
    ModuleContext,
    ModuleManifest,
    ModuleRegistry,
)
from teaf.runtime import Runtime
from teaf.services import Lifetime, ServiceContainer
from teaf.version import CURRENT_VERSION as Version

__all__ = [
    # -- Los catorce símbolos pedidos explícitamente (Sprint 2.5.1, sección 2).
    "Application",
    "Runtime",
    "Module",
    "ModuleBase",
    "ModuleBuilder",
    "ModuleContext",
    "ModuleManifest",
    "ServiceContainer",
    "EventBus",
    "CapabilityRegistry",
    "ModuleRegistry",
    "Health",
    "Configuration",
    "Version",
    # -- Compañeros imprescindibles para usar los símbolos de arriba sin
    # -- tocar ``teaf._internal.*`` — ver docstring del módulo.
    "CapabilityCategory",
    "Event",
    "Lifetime",
    "ModuleCategory",
    "get_configuration",
]
