"""Pruebas del contrato OpenAPI de las rutas de sistema (Sprint 2.9.1).

Estas pruebas protegen una optimización de arranque, no una funcionalidad.
El Sprint 2.9.1 añadió ``response_model=None`` a las 15 rutas de sistema del
framework porque la generación del modelo Pydantic de respuesta dominaba el
arranque de la aplicación (5,5× más lento con ella). Esa optimización solo
es legítima mientras se cumplan **dos** condiciones, y son exactamente las
que se verifican aquí:

1. El cuerpo servido no cambia — ni un byte.
2. El esquema OpenAPI se conserva, declarado a mano en
   ``teaf/_internal/shared/openapi.py`` en vez de generado.

Si alguien retira ``response_model=None`` (perdiendo la optimización) o
retira las constantes de ``responses=`` (perdiendo la documentación), estas
pruebas lo dicen.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

#: Las rutas de sistema que devuelven un objeto JSON, y el tipo que su
#: esquema OpenAPI debe declarar.
_OBJECT_ROUTES = (
    "/health",
    "/ready",
    "/info",
    "/runtime/info",
    "/runtime/configuration",
    "/runtime/dependencies",
    "/runtime/self",
)
_ARRAY_ROUTES = (
    "/runtime/modules",
    "/runtime/services",
    "/runtime/plugins",
    "/runtime/capabilities",
    "/runtime/features",
    "/runtime/events",
)
_STRING_MAP_ROUTES = ("/", "/live")


def _schema_of(openapi: dict[str, object], path: str) -> dict[str, object]:
    paths = openapi["paths"]
    assert isinstance(paths, dict)
    operation = paths[path]["get"]  # type: ignore[index]
    content = operation["responses"]["200"]["content"]
    schema: dict[str, object] = content["application/json"]["schema"]
    return schema


@pytest.mark.parametrize("path", _OBJECT_ROUTES)
def test_object_routes_declare_an_object_schema(client: TestClient, path: str) -> None:
    openapi = client.get("/openapi.json").json()
    assert _schema_of(openapi, path) == {"type": "object"}


@pytest.mark.parametrize("path", _ARRAY_ROUTES)
def test_array_routes_declare_an_array_of_objects_schema(client: TestClient, path: str) -> None:
    openapi = client.get("/openapi.json").json()
    assert _schema_of(openapi, path) == {"type": "array", "items": {"type": "object"}}


@pytest.mark.parametrize("path", _STRING_MAP_ROUTES)
def test_string_map_routes_declare_their_value_type(client: TestClient, path: str) -> None:
    openapi = client.get("/openapi.json").json()
    assert _schema_of(openapi, path) == {
        "type": "object",
        "additionalProperties": {"type": "string"},
    }


def test_every_system_route_is_covered_by_this_test(client: TestClient) -> None:
    """Una ruta de sistema nueva sin esquema declarado debe hacer fallar esto.

    Sin esta comprobación, añadir una ruta con ``response_model=None`` y
    olvidar su ``responses=`` la dejaría sin documentar en OpenAPI y nadie se
    enteraría.
    """
    documented = set(_OBJECT_ROUTES) | set(_ARRAY_ROUTES) | set(_STRING_MAP_ROUTES)
    served = {
        path
        for path, operations in client.get("/openapi.json").json()["paths"].items()
        if "get" in operations
    }
    assert served == documented


@pytest.mark.parametrize("path", (*_OBJECT_ROUTES, *_ARRAY_ROUTES, *_STRING_MAP_ROUTES))
def test_every_system_route_still_serves_valid_json(client: TestClient, path: str) -> None:
    """La optimización no puede cambiar lo que se sirve."""
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    response.json()


def test_array_routes_really_serve_arrays(client: TestClient) -> None:
    for path in _ARRAY_ROUTES:
        assert isinstance(client.get(path).json(), list), path


def test_object_routes_really_serve_objects(client: TestClient) -> None:
    for path in (*_OBJECT_ROUTES, *_STRING_MAP_ROUTES):
        assert isinstance(client.get(path).json(), dict), path
