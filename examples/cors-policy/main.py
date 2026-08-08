"""CORS — política configurable, con comodines de subdominio y credenciales.

Ejecutar:

    python examples/cors-policy/main.py
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf.api import ApiGateway, CorsPolicy, RateLimiter, RateLimitRule

app = FastAPI()


@app.get("/perfil")
def perfil() -> dict[str, str]:
    return {"usuario": "ana"}


politica = CorsPolicy(
    allow_origin_patterns=("https://*.torus.com",),
    allow_methods=("GET", "POST", "OPTIONS"),
    allow_headers=("X-Tenant",),
    expose_headers=("X-Total-Count",),
    allow_credentials=True,
    max_age_seconds=600,
)
# Se añade un límite muy bajo solo para demostrar que las cabeceras CORS
# acompañan también a las respuestas de error.
ApiGateway(
    cors=politica,
    rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=3, window_seconds=60)]),
).install(app)
client = TestClient(app)


print("== Comodín de subdominio: qué orígenes acepta la política ==")
for origen in (
    "https://app.torus.com",
    "https://portal.torus.com",
    "https://torus.com",
    "https://evil-torus.com",
):
    print(f"  {origen:<28} {'permitido' if politica.is_origin_allowed(origen) else 'RECHAZADO'}")

print("\n== Comprobación previa (preflight) ==")
for origen in ("https://app.torus.com", "https://evil.com"):
    response = client.options(
        "/perfil",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Tenant",
        },
    )
    print(
        f"  {origen:<26} HTTP {response.status_code} | "
        f"Allow-Origin={response.headers.get('Access-Control-Allow-Origin', '-')} | "
        f"Max-Age={response.headers.get('Access-Control-Max-Age', '-')}"
    )

print("\n== Petición normal: credenciales nunca viajan con comodín ==")
response = client.get("/perfil", headers={"Origin": "https://app.torus.com"})
print(f"  Allow-Origin      = {response.headers['Access-Control-Allow-Origin']}")
print(f"  Allow-Credentials = {response.headers['Access-Control-Allow-Credentials']}")
print(f"  Expose-Headers    = {response.headers['Access-Control-Expose-Headers']}")
print(f"  Vary              = {response.headers['Vary']}")

print("\n== Las cabeceras CORS acompañan también a los errores ==")
for _ in range(3):
    response = client.get("/perfil", headers={"Origin": "https://app.torus.com"})
print(
    f"  HTTP {response.status_code} | "
    f"Allow-Origin={response.headers.get('Access-Control-Allow-Origin', 'AUSENTE')}"
)
