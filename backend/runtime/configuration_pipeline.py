"""``ConfigurationPipeline`` — validación de configuración por módulo en el arranque.

Cada módulo puede registrar un validador propio (una función sin argumentos
que lanza si su configuración es inválida). ``Runtime.startup()`` ejecuta
``validate_all()`` durante la etapa ``BOOTSTRAP``, antes de que corra el
``StartupPipeline`` — un módulo mal configurado detiene el arranque con un
error claro en vez de fallar más tarde de forma confusa.
"""

from __future__ import annotations

from collections.abc import Callable

from backend.core.exceptions import ConfigurationException

#: Un validador no recibe argumentos; lanza si la configuración es inválida.
ConfigValidator = Callable[[], None]


class ConfigurationPipeline:
    """Registro de validadores de configuración, uno por módulo."""

    def __init__(self) -> None:
        self._validators: dict[str, ConfigValidator] = {}

    def register(self, module_name: str, validator: ConfigValidator) -> None:
        """Registra ``validator`` para ejecutarse por ``module_name`` en ``validate_all()``."""
        self._validators[module_name] = validator

    def registered_modules(self) -> tuple[str, ...]:
        """Nombres de los módulos con validador registrado."""
        return tuple(self._validators)

    def validate_all(self) -> None:
        """Ejecuta todos los validadores registrados, en orden de registro.

        Raises:
            ConfigurationException: si algún validador falla — se envuelve
                (salvo que ya sea una ``ConfigurationException``) indicando
                qué módulo falló.
        """
        for module_name, validator in self._validators.items():
            try:
                validator()
            except ConfigurationException:
                raise
            except Exception as exc:
                raise ConfigurationException(
                    f"Configuración inválida para el módulo '{module_name}': {exc}"
                ) from exc
