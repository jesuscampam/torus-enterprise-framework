"""Configuración tipada por entorno (Configuration by Environment).

Cada entorno (``development``/``testing``/``staging``/``production``) tiene
su propia subclase de ``Settings`` con valores por defecto sensatos para ese
entorno; cualquier valor puede sobrescribirse vía variable de entorno o
archivo ``.env`` (ver ``.env.example`` en la raíz), nunca hardcodeado.

Añadir un parámetro de configuración nuevo es tan simple como declarar un
campo tipado más en ``Settings`` — no requiere tocar ``environment.py`` ni el
resto del framework (ver docs/core/CORE.md, "Cómo extender el Core").
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.config.environment import Environment, get_environment
from backend.core.logging import LogFormat


class Settings(BaseSettings):
    """Configuración base. No se instancia directamente: usar ``get_settings()``."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "TEAF"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False

    # Preparado para Azure App Service / Docker / Render: ambos inyectan
    # PORT en runtime; HOST 0.0.0.0 es obligatorio para escuchar dentro de
    # un contenedor.
    host: str = "0.0.0.0"
    port: int = 8000

    log_level: str = "INFO"
    log_format: LogFormat = "console"
    log_file: str | None = None

    docs_enabled: bool = True


class DevelopmentSettings(Settings):
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    log_level: str = "DEBUG"
    log_format: LogFormat = "console"
    docs_enabled: bool = True


class TestingSettings(Settings):
    environment: Environment = Environment.TESTING
    debug: bool = True
    log_level: str = "WARNING"
    log_format: LogFormat = "console"
    docs_enabled: bool = True


class StagingSettings(Settings):
    environment: Environment = Environment.STAGING
    debug: bool = False
    log_level: str = "INFO"
    log_format: LogFormat = "json"
    docs_enabled: bool = True


class ProductionSettings(Settings):
    environment: Environment = Environment.PRODUCTION
    debug: bool = False
    log_level: str = "INFO"
    log_format: LogFormat = "json"
    #: Swagger/OpenAPI deshabilitado por defecto en producción.
    docs_enabled: bool = False


_SETTINGS_BY_ENVIRONMENT: dict[Environment, type[Settings]] = {
    Environment.DEVELOPMENT: DevelopmentSettings,
    Environment.TESTING: TestingSettings,
    Environment.STAGING: StagingSettings,
    Environment.PRODUCTION: ProductionSettings,
}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Resuelve la configuración de la instancia en ejecución (cacheada por proceso).

    Selecciona la subclase de ``Settings`` según ``ENVIRONMENT`` y aplica
    sobre ella cualquier variable de entorno / ``.env`` presente.
    """
    environment = get_environment()
    settings_cls = _SETTINGS_BY_ENVIRONMENT[environment]
    return settings_cls()
