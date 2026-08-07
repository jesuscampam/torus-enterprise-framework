"""API audit — registro completo de cada petición, integrado con Observability.

Cada entrada lleva correlation/trace/span-id, identidad, tenant, latencia y
desenlace, de modo que desde una entrada de auditoría se salta a la traza
completa de esa petición.

Ejecutar:

    python examples/api-audit/main.py
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from teaf import Event
from teaf.api import (
    ApiAudit,
    ApiGateway,
    InMemoryAuditSink,
    LoggingAuditSink,
    RateLimiter,
    RateLimitRule,
)

app = FastAPI()


@app.get("/pedidos")
def listar() -> dict[str, list[str]]:
    return {"pedidos": ["P-1", "P-2"]}


@app.get("/roto")
def roto() -> dict[str, str]:
    raise RuntimeError("fallo simulado del endpoint")


# Dos destinos a la vez: uno en memoria (inspeccionable desde el proceso) y
# otro que emite cada entrada como log estructurado.
memoria = InMemoryAuditSink(limit=100)
auditoria = ApiAudit([memoria, LoggingAuditSink()])

ApiGateway(
    audit=auditoria,
    rate_limiter=RateLimiter([RateLimitRule(name="ip", limit=2, window_seconds=60)]),
).install(app)

client = TestClient(app, raise_server_exceptions=False)

print("== Se auditan las peticiones correctas, las rechazadas y las fallidas ==")
client.get("/pedidos", headers={"X-Correlation-ID": "corr-001"})
client.get("/roto", headers={"X-Correlation-ID": "corr-002"})
client.get("/pedidos", headers={"X-Correlation-ID": "corr-003"})  # rechazada: límite 2

print(f"\n  {'MÉTODO':<7} {'RUTA':<10} {'HTTP':<5} {'DESENLACE':<10} {'LATENCIA':<10} CORRELACIÓN")
for registro in memoria.records:
    print(
        f"  {registro.method:<7} {registro.path:<10} {registro.status_code:<5} "
        f"{registro.outcome.value:<10} {registro.latency_seconds * 1000:>6.1f} ms   "
        f"{registro.correlation_id}"
    )

print("\n== Todo lo que lleva una entrada de auditoría ==")
for clave, valor in memoria.records[0].as_dict().items():
    print(f"  {clave:<16} {valor}")

print("\n== La auditoría también publica eventos en el EventBus del Runtime ==")
print("  (con ApiProtectionModule dentro de Application, 'audit.recorded' llega")
print("   a cualquier módulo suscrito — ver docs/api/AUDIT.md)")
print(f"  ejemplo de evento: {Event(name='audit.recorded', payload={'path': '/pedidos'}).name}")
