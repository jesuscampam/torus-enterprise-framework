"""Constantes centralizadas del framework.

Cualquier literal usado en más de un módulo debe vivir aquí — nunca
repetirse (principio DRY, ver docs/standards/CODING-STANDARD.md).
"""

from __future__ import annotations

#: Header HTTP usado para propagar el correlation-id entre cliente y
#: servidor (ver docs/standards/LOGGING-STANDARD.md, sección 2, y
#: docs/diagrams/security-architecture.mmd).
HEADER_CORRELATION_ID = "X-Correlation-Id"

#: Nombre de servicio por defecto incluido en cada log estructurado.
DEFAULT_SERVICE_NAME = "teaf-backend"

#: Nombre del framework, usado como valor por defecto de ``app_name``.
FRAMEWORK_NAME = "TEAF"
