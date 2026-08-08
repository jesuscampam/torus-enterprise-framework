"""Response compression — GZip (estándar) y Brotli (paquete opcional).

Ejecutar:

    python examples/response-compression/main.py
"""

from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf.api import (
    ApiGateway,
    BrotliCompressionProvider,
    CompressionNegotiator,
    CompressionPolicy,
    GzipCompressionProvider,
    parse_accept_encoding,
)

app = FastAPI()


@app.get("/catalogo")
def catalogo() -> dict[str, object]:
    return {
        "productos": [{"sku": f"SKU-{i:05d}", "nombre": "Producto de ejemplo"} for i in range(200)]
    }


@app.get("/ping")
def ping() -> dict[str, str]:
    return {"pong": "ok"}


gzip_provider = GzipCompressionProvider()
brotli_provider = BrotliCompressionProvider()

print("== Proveedores disponibles en este intérprete ==")
print(f"  gzip : disponible={gzip_provider.available} (librería estándar)")
print(
    f"  br   : disponible={brotli_provider.available}"
    f"{'' if brotli_provider.available else '  → pip install brotli para activarlo'}"
)

print("\n== Negociación: manda la preferencia del cliente ==")
for cabecera in ("gzip", "br, gzip", "gzip;q=0.5, br;q=1.0", "identity", ""):
    print(
        f"  Accept-Encoding: {cabecera!r:<28} → orden preferido {parse_accept_encoding(cabecera)}"
    )

ApiGateway(
    compression=CompressionNegotiator(
        [brotli_provider, gzip_provider], policy=CompressionPolicy(minimum_size_bytes=500)
    )
).install(app)
client = TestClient(app)

print("\n== Sobre HTTP: qué se comprime y qué no ==")
for ruta, cabecera in (
    ("/catalogo", "gzip"),
    ("/catalogo", "identity"),
    ("/ping", "gzip"),
):
    response = client.get(ruta, headers={"Accept-Encoding": cabecera})
    codificacion = response.headers.get("Content-Encoding", "sin comprimir")
    en_red = response.headers.get("Content-Length", "?")
    original = len(json.dumps(response.json(), separators=(",", ":")).encode())
    print(
        f"  GET {ruta:<11} Accept-Encoding={cabecera:<9} → {codificacion:<13} "
        f"{en_red:>6} bytes en red / {original} sin comprimir"
    )

print("\n  (una respuesta pequeña no se comprime: el ahorro no compensa la CPU)")
