"""Contrato HTTP del que depende el frontend MVP (Sprint 3.5c).

El frontend mantiene sus tipos a mano en ``frontend/src/types/runtime.ts``: no
hay generación desde OpenAPI todavía (ver docs/roadmap/BACKLOG.md). Un fichero
de tipos escrito a mano se desincroniza en silencio —el backend renombra un
campo, TypeScript sigue compilando porque no sabe nada del servidor, y el fallo
aparece en el navegador—, así que **estas pruebas son la costura que lo impide**:
declaran la forma que el frontend espera y la verifican contra el TEAF real.

Dos propiedades se comprueban a la vez:

1. **Superficie pública.** La aplicación se construye con ``from teaf import
   Application``, el mismo import que usaría cualquier consumidor externo. Si
   estos endpoints dejaran de existir en una ``Application`` estándar, el
   frontend no podría hablar con TEAF sin tocar internos.
2. **Forma de la respuesta.** Cada campo que el frontend lee existe y tiene el
   tipo declarado.

No se comprueba el contenido —cuántos módulos hay, cómo se llaman—: eso depende
de qué registre cada aplicación y no es contrato.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

import pytest
from fastapi.testclient import TestClient
from teaf import Application

#: Cada entrada declara: campo → tipos aceptados. ``None`` en la tupla significa
#: que el backend puede emitir ``null`` ahí, y el tipo del frontend lo refleja.
FieldSpec = Mapping[str, tuple[type | None, ...]]


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Cliente contra una ``Application`` construida por la API pública.

    Deliberadamente **no** usa la fixture ``app`` de ``conftest.py``: aquella
    llama a ``create_app`` de ``teaf._internal``, y aquí lo que se valida es
    justamente que el consumidor externo no necesita bajar hasta ahí.
    """
    with TestClient(Application()) as test_client:
        yield test_client


def assert_fields(payload: Mapping[str, Any], spec: FieldSpec, *, where: str) -> None:
    """Verifica que ``payload`` tiene cada campo de ``spec`` con un tipo aceptado."""
    for field, accepted in spec.items():
        assert field in payload, f"{where}: falta el campo '{field}' que el frontend lee"

        value = payload[field]
        if value is None:
            assert None in accepted, f"{where}: '{field}' llegó null y el frontend no lo admite"
            continue

        concrete = tuple(t for t in accepted if t is not None)
        assert isinstance(value, concrete), (
            f"{where}: '{field}' es {type(value).__name__}, "
            f"y el frontend espera {', '.join(t.__name__ for t in concrete)}"
        )


# --- Endpoints de sistema -------------------------------------------------


def test_health_matches_frontend_health_info(client: TestClient) -> None:
    """``GET /health`` — consumido por el panel (`useHealth`)."""
    response = client.get("/health")
    assert response.status_code == 200

    body = response.json()
    assert_fields(
        body,
        {
            "status": (str,),
            "name": (str,),
            "version": (str,),
            "environment": (str,),
            "buildDate": (str,),
            "modules": (dict,),
        },
        where="GET /health",
    )
    # El panel decide entre «Operativo» y «Degradado» comparando con "ok".
    assert body["status"] in {"ok", "degraded"}
    assert_fields(
        body["modules"], {"status": (str,), "checks": (dict,)}, where="GET /health .modules"
    )


def test_info_matches_frontend_framework_info(client: TestClient) -> None:
    """``GET /info`` — versión, entorno y módulos declarados."""
    response = client.get("/info")
    assert response.status_code == 200

    body = response.json()
    assert_fields(
        body,
        {
            "name": (str,),
            "version": (str,),
            "environment": (str,),
            "buildDate": (str,),
            "modules": (list,),
            "state": (str,),
            "lifecycleStage": (str, None),
            "loadedModules": (list,),
            "registeredCapabilities": (list,),
        },
        where="GET /info",
    )
    for module in body["modules"]:
        assert_fields(
            module,
            {"name": (str,), "version": (str,), "status": (str,)},
            where="GET /info .modules[]",
        )


# --- Runtime --------------------------------------------------------------


def test_runtime_info_matches_frontend_diagnostics(client: TestClient) -> None:
    """``GET /runtime/info`` — contadores y métricas del panel."""
    response = client.get("/runtime/info")
    assert response.status_code == 200

    assert_fields(
        response.json(),
        {
            "runtimeId": (str,),
            "startupTime": (str, None),
            "runningTimeSeconds": (int, float),
            "registeredModules": (int,),
            "registeredServices": (int,),
            "registeredCapabilities": (int,),
            "registeredPlugins": (int,),
            "registeredFeatures": (int,),
            "frameworkVersion": (str,),
            "pythonVersion": (str,),
            "configurationSummary": (dict,),
            "dependencyGraphSummary": (dict,),
            "containerStatistics": (dict,),
            # El panel muestra «no disponible» cuando el anfitrión no los mide
            # (plataformas sin `resource`, ver el parche de Windows del 3.0).
            "memoryRssBytes": (int, None),
            "cpuTimeSeconds": (int, float, None),
        },
        where="GET /runtime/info",
    )


def test_runtime_modules_matches_frontend_descriptor(client: TestClient) -> None:
    """``GET /runtime/modules`` — la tabla de la pantalla de módulos."""
    response = client.get("/runtime/modules")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    # Una `Application` estándar registra sus módulos de infraestructura, así que
    # esta colección no está vacía y la tabla se puede verificar con datos reales.
    assert body, "una Application estándar debería registrar módulos de infraestructura"

    for module in body:
        assert_fields(
            module,
            {
                "id": (str,),
                "name": (str,),
                "version": (str,),
                "author": (str, None),
                "description": (str,),
                "status": (str,),
                "lifecycleState": (str,),
                "capabilities": (list,),
                "dependencies": (list,),
                "tags": (list,),
                "documentation": (str, None),
                "experimental": (bool,),
                "createdAt": (str,),
                "updatedAt": (str,),
            },
            where="GET /runtime/modules[]",
        )


def test_runtime_events_matches_frontend_event(client: TestClient) -> None:
    """``GET /runtime/events`` — historial del EventBus."""
    response = client.get("/runtime/events")
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list)
    # El arranque publica `framework.started`, así que hay historial que mostrar.
    assert body, "el arranque debería haber publicado eventos"

    for event in body:
        assert_fields(event, {"name": (str,), "payload": (dict,)}, where="GET /runtime/events[]")


def test_runtime_events_limit_is_a_real_server_side_filter(client: TestClient) -> None:
    """El filtro de la pantalla de eventos **recorta en el servidor**, no en el cliente.

    Es la única entrada de formulario del MVP que llega al backend; si el
    parámetro dejara de aplicarse, la pantalla mostraría un número correcto
    sobre datos que el servidor nunca acotó.
    """
    everything = client.get("/runtime/events").json()
    assert len(everything) >= 2, "hacen falta al menos dos eventos para probar el recorte"

    limited = client.get("/runtime/events", params={"limit": 1}).json()

    assert len(limited) == 1
    assert len(limited) < len(everything)


@pytest.mark.parametrize(
    ("path", "spec"),
    [
        ("/runtime/services", {"serviceId": (str,), "contract": (str,), "lifetime": (str,)}),
        ("/runtime/capabilities", {"id": (str,), "name": (str,)}),
        (
            "/runtime/features",
            {
                "id": (str,),
                "name": (str,),
                "description": (str,),
                "group": (str,),
                "status": (str,),
                "tags": (list,),
                "createdAt": (str,),
                "updatedAt": (str,),
            },
        ),
        ("/runtime/plugins", {"name": (str,), "version": (str,)}),
    ],
)
def test_runtime_inventory_collections_are_json_arrays(
    client: TestClient, path: str, spec: FieldSpec
) -> None:
    """Las cuatro colecciones del inventario del Runtime.

    En un TEAF desnudo llegan vacías —solo se llenan cuando una aplicación
    registra lo suyo— y esa es la razón de que la pantalla de Runtime muestre
    sobre todo estados vacíos. Aquí se verifica el **tipo contenedor** siempre, y
    la forma de los elementos solo cuando los hay: exigir contenido convertiría
    una propiedad del framework en un requisito del contrato.
    """
    response = client.get(path)
    assert response.status_code == 200

    body = response.json()
    assert isinstance(body, list), f"{path} debe devolver un array JSON"

    for item in body:
        assert_fields(item, spec, where=f"GET {path}[]")


def test_runtime_collections_are_bare_arrays_without_pagination(client: TestClient) -> None:
    """Estas colecciones **no** usan el sobre `CollectionEnvelope` de API-STANDARD.md §4.

    Está anotado como limitación conocida y como entrada de backlog. La prueba
    fija el hecho: mientras siga siendo cierto, el frontend no debe ofrecer
    controles de paginación, porque no hay `meta` con la que calcularlos. El día
    que el backend adopte el sobre, esta prueba falla y avisa de que la
    limitación se puede levantar.
    """
    for path in ("/runtime/modules", "/runtime/events", "/runtime/services"):
        body = client.get(path).json()
        assert isinstance(body, list), f"{path} dejó de ser un array desnudo"


# --- Errores y correlación ------------------------------------------------


def test_unknown_route_returns_problem_details_the_frontend_can_render(
    client: TestClient,
) -> None:
    """Un 404 llega como Problem Details con `correlationId`.

    `ApiError` del frontend se construye con esta forma y `ErrorState` muestra el
    `correlationId` como referencia para soporte; sin él, un error visto en el
    navegador no se puede cruzar con su traza en el servidor.
    """
    response = client.get("/no-existe")

    assert response.status_code == 404
    assert_fields(
        response.json(),
        {"type": (str,), "title": (str,), "status": (int,), "correlationId": (str,)},
        where="GET /no-existe",
    )


def test_correlation_id_travels_from_the_client_to_the_response(client: TestClient) -> None:
    """El backend respeta el `X-Correlation-Id` que envía el `HttpClient`.

    El cliente del frontend genera uno por petición; si el backend lo ignorara y
    generara el suyo, la referencia que se le enseña al usuario no coincidiría
    con la de los logs.
    """
    sent = "3d1f0c7a-0000-4000-8000-frontendmvp01"

    response = client.get("/no-existe", headers={"X-Correlation-Id": sent})

    assert response.json()["correlationId"] == sent
