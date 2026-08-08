"""Idempotencia — un reintento no debe crear dos pedidos.

El problema que resuelve: el cliente envía ``POST /pedidos``, la respuesta se
pierde por un corte de red y el cliente reintenta. Sin idempotencia se crean
dos pedidos.

Ejecutar:

    python examples/idempotent-requests/main.py
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf.api import ApiGateway, IdempotencyManager, build_fingerprint

app = FastAPI()
pedidos_creados: list[str] = []


@app.post("/pedidos")
def crear_pedido(pedido: dict[str, str]) -> dict[str, str]:
    """Deliberadamente no idempotente: cada llamada crea un pedido nuevo."""
    identificador = str(uuid.uuid4())
    pedidos_creados.append(identificador)
    return {"id": identificador, "sku": pedido["sku"]}


ApiGateway(idempotency=IdempotencyManager(ttl_seconds=86_400)).install(app)
client = TestClient(app)


def enviar(titulo: str, *, sku: str, clave: str | None) -> None:
    cabeceras = {"Idempotency-Key": clave} if clave else {}
    response = client.post("/pedidos", json={"sku": sku}, headers=cabeceras)
    reproducida = response.headers.get("X-Idempotent-Replay") == "true"
    detalle = response.json()
    resultado = detalle.get("id", detalle.get("detail", ""))
    marca = " (REPRODUCIDA)" if reproducida else ""
    print(f"  {titulo:<44} HTTP {response.status_code} → {str(resultado)[:36]}{marca}")


print("== Sin clave de idempotencia: cada intento crea un pedido ==")
enviar("POST sku=A (sin clave)", sku="A", clave=None)
enviar("POST sku=A (sin clave, reintento)", sku="A", clave=None)
print(f"  pedidos creados hasta ahora: {len(pedidos_creados)}")

print("\n== Con clave: el reintento reproduce la respuesta original ==")
enviar("POST sku=B  Idempotency-Key: pedido-42", sku="B", clave="pedido-42")
enviar("POST sku=B  Idempotency-Key: pedido-42", sku="B", clave="pedido-42")
print(f"  pedidos creados hasta ahora: {len(pedidos_creados)}  (solo uno más)")

print("\n== Misma clave con cuerpo distinto: conflicto, no reproducción ==")
enviar("POST sku=C  Idempotency-Key: pedido-42", sku="C", clave="pedido-42")

print("\n== La huella depende de método, ruta y cuerpo ==")
base = build_fingerprint(method="POST", path="/pedidos", body=b'{"sku":"B"}')
otro = build_fingerprint(method="POST", path="/pedidos", body=b'{"sku":"C"}')
print(f"  sku=B → {base[:16]}...")
print(f"  sku=C → {otro[:16]}...   (distinta: por eso el tercer intento dio 409)")
