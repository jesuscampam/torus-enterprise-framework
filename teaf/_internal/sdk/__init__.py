"""Module SDK — Sprint 2.5 (Developer Platform).

El SDK oficial para construir módulos de TEAF: un desarrollador crea un
módulo completo heredando únicamente de ``ModuleBase`` (``module_base.py``)
y describiéndolo con un ``ModuleManifest`` (``manifest.py``, normalmente
construido con ``ModuleBuilder``, ``builder.py``). Toda la infraestructura
de registro (servicios, capacidades, módulo en el ``ModuleRegistry``) se
cablea automáticamente contra el ``Runtime`` (Sprint 2.3) y su Platform
Intelligence (Sprint 2.4) — el desarrollador nunca llama directamente a
``ServiceContainer.register_*`` ni a ``CapabilityRegistry.register``.

A diferencia de ``teaf/_internal/runtime/`` (que nunca depende de
``teaf/_internal/contracts/`` ni ``teaf/_internal/providers/``), el SDK **sí** depende de
``teaf/_internal/core/`` y ``teaf/_internal/runtime/`` — es la capa que se apoya en ambos
para ofrecer una experiencia de autoría de módulos de alto nivel. Ningún
módulo real (Database, Security, AI, ...) se implementa con este SDK en
este Sprint — es infraestructura de autoría, no una migración de los
módulos existentes.
"""

from __future__ import annotations

#: Versión del propio SDK — independiente de ``FRAMEWORK_VERSION``
#: (``teaf/_internal/core/application.py``). Un módulo declara compatibilidad con
#: un rango de esta versión vía ``ModuleManifest.sdk_compatibility``, nunca
#: contra ``FRAMEWORK_VERSION`` directamente — así el SDK puede evolucionar
#: (nuevas primitivas, nuevos binders) a un ritmo distinto del framework.
SDK_VERSION = "1.0.0"
