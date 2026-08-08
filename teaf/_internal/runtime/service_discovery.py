"""``ServiceDiscovery`` — consulta de servicios registrados en el ``ServiceContainer``.

Capa fina de solo-lectura sobre ``ServiceContainer``: no registra ni
modifica nada, solo responde preguntas (¿qué hay?, ¿de qué depende?, ¿qué
capacidades aporta?) — consumida por ``GET /runtime/dependencies`` y por el
Developer API (``backend/developer/runtime_api.py``).
"""

from __future__ import annotations

from teaf._internal.runtime.container import ServiceContainer, ServiceMetadata
from teaf._internal.runtime.exceptions import ServiceNotRegisteredException


class ServiceDiscovery:
    """Búsqueda y descripción de servicios, apoyada en ``ServiceContainer.describe_services()``."""

    def __init__(self, container: ServiceContainer) -> None:
        self._container = container

    def list(self) -> tuple[ServiceMetadata, ...]:
        """Metadata de todos los servicios registrados."""
        return self._container.describe_services()

    def search(self, query: str) -> tuple[ServiceMetadata, ...]:
        """Búsqueda simple por subcadena en ``service_id``, ``name`` o ``tags``."""
        query_lower = query.lower()
        return tuple(
            service
            for service in self.list()
            if query_lower in service.service_id.lower()
            or query_lower in service.name.lower()
            or any(query_lower in tag.lower() for tag in service.tags)
        )

    def resolve(self, contract: type) -> object:
        """Resuelve ``contract`` contra el ``ServiceContainer`` subyacente.

        Raises:
            ServiceNotRegisteredException: si nadie registró ``contract``.
        """
        return self._container.resolve(contract)

    def describe(self, service_id: str) -> ServiceMetadata:
        """Devuelve la metadata del servicio ``service_id``.

        Raises:
            ServiceNotRegisteredException: si no hay ningún servicio
                registrado con ese ``service_id``.
        """
        for service in self.list():
            if service.service_id == service_id:
                return service
        raise ServiceNotRegisteredException(
            f"No hay ningún servicio registrado como '{service_id}'."
        )

    def capabilities(self, service_id: str) -> tuple[str, ...]:
        """Capacidades declaradas por el servicio ``service_id``.

        Raises:
            ServiceNotRegisteredException: si no existe.
        """
        return self.describe(service_id).capabilities

    def dependency_tree(self, service_id: str) -> dict[str, object]:
        """Árbol de dependencias declaradas de ``service_id``, expandido recursivamente.

        Los ``service_id`` sin metadata registrada en este ``ServiceContainer``
        se listan como hojas sin expandir (no todo lo declarado en
        ``dependencies`` tiene por qué estar registrado aquí). Protegido
        contra ciclos: un ``service_id`` ya visitado en la rama actual no se
        vuelve a expandir.

        Raises:
            ServiceNotRegisteredException: si ``service_id`` no existe.
        """
        return self._build_tree(service_id, visited=set())

    def _build_tree(self, service_id: str, *, visited: set[str]) -> dict[str, object]:
        service = self.describe(service_id)
        if service_id in visited:
            return {"id": service_id, "dependencies": []}
        visited = visited | {service_id}

        children: list[dict[str, object]] = []
        for dependency_id in service.dependencies:
            if any(s.service_id == dependency_id for s in self.list()):
                children.append(self._build_tree(dependency_id, visited=visited))
            else:
                children.append({"id": dependency_id, "dependencies": []})

        return {"id": service_id, "dependencies": children}
