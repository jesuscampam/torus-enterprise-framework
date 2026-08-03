"""``teaf.configuration`` — configuración tipada por entorno.

``Configuration`` es un alias de ``Settings`` (``backend/config/settings.py``,
Sprint 2.1) y ``get_configuration`` de ``get_settings`` — mismos objetos,
nombres neutrales para la superficie pública en vez del vocabulario interno
"Settings" (que además choca con el ``Settings`` de ``pydantic-settings``
del que hereda).
"""

from __future__ import annotations

from backend.config.settings import Settings, get_settings

#: Alias público de ``Settings`` — ver docstring del módulo.
Configuration = Settings
#: Alias público de ``get_settings`` — ver docstring del módulo.
get_configuration = get_settings

__all__ = ["Configuration", "get_configuration"]
