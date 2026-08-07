"""API versioning — las tres formas de declarar versión y la deprecación.

TEAF implementa URI, cabecera y tipo de medio, y deja la elección —o la
combinación— a cada aplicación. Lo que garantiza es que la versión esté
resuelta, validada y comunicada al cliente.

Ejecutar:

    python examples/api-versioning/main.py
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from teaf.api import ApiGateway, ApiVersion, ApiVersioningPolicy, ApiVersionNegotiator

app = FastAPI()


@app.get("/api/v1/orders")
@app.get("/api/v2/orders")
@app.get("/orders")
def orders(request: Request) -> dict[str, str]:
    """El endpoint lee la versión ya negociada de ``request.state``.

    TEAF **no** enruta por versión a propósito: elegir qué implementación
    atiende cada versión (dos routers, una rama, dos despliegues) es una
    decisión de la aplicación.
    """
    negotiation = request.state.api_version
    return {
        "servido_con": str(negotiation.version),
        "via": negotiation.strategy.value if negotiation.strategy else "por-defecto",
    }


gateway = ApiGateway(
    versioning=ApiVersionNegotiator(
        ApiVersioningPolicy(
            supported=(ApiVersion(1), ApiVersion(2)),
            default=ApiVersion(1),
            deprecated={"v1": "Wed, 31 Dec 2026 23:59:59 GMT"},
        )
    )
)
gateway.install(app)
client = TestClient(app)


def show(titulo: str, **kwargs: object) -> None:
    response = client.get(**kwargs)  # type: ignore[arg-type]
    cuerpo = response.json()
    print(f"  {titulo:<38} HTTP {response.status_code}", end="")
    if response.status_code == 200:
        print(
            f" | {cuerpo['servido_con']} (via {cuerpo['via']})"
            f" | Deprecation={response.headers.get('Deprecation', '-')}"
        )
    else:
        print(f" | {cuerpo['detail']}")


print("== Las tres estrategias de versionado ==")
show("URI      /api/v2/orders", url="/api/v2/orders")
show("Cabecera X-API-Version: 2", url="/orders", headers={"X-API-Version": "2"})
show(
    "Tipo de medio vnd.teaf.v2+json",
    url="/orders",
    headers={"Accept": "application/vnd.teaf.v2+json"},
)

print("\n== Versión por defecto y deprecación ==")
show("sin declarar versión", url="/orders")
show("v1 (obsoleta)", url="/api/v1/orders")

print("\n== Versión no soportada (política estricta) ==")
show("v9", url="/orders", headers={"X-API-Version": "9"})
