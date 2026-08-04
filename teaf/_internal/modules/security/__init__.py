"""``SecurityModule`` — la plataforma de seguridad de TEAF, sobre el Module SDK.

Mismo patrón que ``modules/database/`` (Sprint 2.6): un ``ModuleBase``
que construye todo lo concreto en ``__init__`` y declara sus
capacidades/servicios/eventos vía ``ModuleBuilder`` en ``manifest.py`` —
nada se registra a mano contra el ``ServiceContainer``/``CapabilityRegistry``,
lo hace el SDK durante ``bootstrap()``.
"""

from __future__ import annotations
