"""Carga y validación del entorno de ejecución.

TEAF soporta cuatro entornos (ver docs/architecture/FRAMEWORK-BLUEPRINT.md,
Sprint 2.1): ``development``, ``testing``, ``staging`` y ``production``. El
entorno se resuelve exclusivamente desde la variable ``ENVIRONMENT`` — nunca
se infiere ni se hardcodea (principio Configuration by Environment, ver
docs/architecture/ARCHITECTURE.md).
"""

from __future__ import annotations

import os
from enum import Enum

from backend.core.exceptions import ConfigurationException

_ENVIRONMENT_VAR = "ENVIRONMENT"


class Environment(str, Enum):
    """Entornos de ejecución soportados por el framework."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


def get_environment() -> Environment:
    """Lee y valida la variable ``ENVIRONMENT``.

    Raises:
        ConfigurationException: si la variable tiene un valor que no
            corresponde a ningún entorno soportado.
    """
    raw_value = os.getenv(_ENVIRONMENT_VAR, Environment.DEVELOPMENT.value).strip().lower()
    try:
        return Environment(raw_value)
    except ValueError as exc:
        valid_values = ", ".join(environment.value for environment in Environment)
        raise ConfigurationException(
            f"Valor de {_ENVIRONMENT_VAR}='{raw_value}' inválido. "
            f"Valores permitidos: {valid_values}."
        ) from exc
