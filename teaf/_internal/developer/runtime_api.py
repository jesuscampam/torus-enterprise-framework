"""``DeveloperRuntimeAPI`` — el Runtime consumido directamente, sin HTTP.

Mismo contenido que ``backend/runtime/api.py`` (``GET /runtime/*``), pero
pensado para código Python que corre en el mismo proceso — un script de
mantenimiento, una consola interactiva, un plugin, o un futuro servidor MCP
(ver Sprint 2.4, ítems 13 y 15). Reutiliza las funciones ``build_*_payload``
de ``backend/runtime/api.py`` para no duplicar el ensamblado de datos: la
única diferencia entre ambos es la capa de transporte (HTTP vs. llamada
directa), nunca la forma de los datos.
"""

from __future__ import annotations

from collections.abc import Mapping

from teaf._internal.runtime.api import (
    ConfigurationProvider,
    build_capabilities_payload,
    build_dependencies_payload,
    build_events_payload,
    build_features_payload,
    build_modules_payload,
    build_plugins_payload,
    build_services_payload,
    default_configuration_provider,
)
from teaf._internal.runtime.runtime import Runtime


class DeveloperRuntimeAPI:
    """Fachada de solo lectura sobre un ``Runtime``, para consumo directo en proceso."""

    def __init__(
        self,
        runtime: Runtime,
        *,
        configuration_provider: ConfigurationProvider = default_configuration_provider,
    ) -> None:
        self._runtime = runtime
        self._configuration_provider = configuration_provider

    def info(self) -> dict[str, object]:
        """Diagnóstico operativo del Runtime (equivalente a ``GET /runtime/info``)."""
        return self._runtime.diagnostics(
            configuration_summary=self._configuration_provider()
        ).as_dict()

    def modules(self) -> list[dict[str, object]]:
        """Metadata de todos los módulos registrados."""
        return build_modules_payload(self._runtime)

    def services(self) -> list[dict[str, object]]:
        """Metadata de todos los servicios registrados."""
        return build_services_payload(self._runtime)

    def plugins(self) -> list[dict[str, object]]:
        """Metadata de todos los plugins cargados."""
        return build_plugins_payload(self._runtime)

    def capabilities(self) -> list[dict[str, object]]:
        """Metadata de todas las capacidades registradas."""
        return build_capabilities_payload(self._runtime)

    def features(self) -> list[dict[str, object]]:
        """Metadata de todos los feature flags registrados."""
        return build_features_payload(self._runtime)

    def events(self, *, limit: int | None = None) -> list[dict[str, object]]:
        """Historial de eventos publicados en el ``EventBus`` del Runtime."""
        return build_events_payload(self._runtime, limit=limit)

    def configuration(self) -> Mapping[str, object]:
        """Resumen de configuración aportado por el composition root."""
        return self._configuration_provider()

    def dependencies(self) -> dict[str, object]:
        """Grafo de dependencias de módulos y árbol de dependencias de servicios."""
        return build_dependencies_payload(self._runtime)
