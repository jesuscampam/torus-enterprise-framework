# idempotent-requests/

Idempotencia gestionada por `Idempotency-Key` en `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)).

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- **La clave la pone el cliente** (`Idempotency-Key`): solo él sabe qué dos peticiones son "la misma intención de negocio".
- **La huella la pone el servidor** (SHA-256 de método + ruta + cuerpo). Reutilizar una clave con un cuerpo distinto no es un reintento, es un error del cliente — y devolver la respuesta antigua lo ocultaría. De ahí el `409` — ver [IDEMPOTENCY.md](../../docs/api/IDEMPOTENCY.md).
- Solo aplica a `POST` y `PATCH`: `GET`/`PUT`/`DELETE` ya son idempotentes por definición de HTTP.
- **Solo se guardan respuestas que no sean 5xx**: cachear un `500` condenaría al cliente a recibir ese mismo error durante todo el TTL, incluso cuando la causa ya estuviera resuelta.
- La respuesta reproducida lleva `X-Idempotent-Replay: true`, y la auditoría la registra con desenlace `replayed` en lugar de `accepted`.
- El middleware es el más **interno** de la cadena: guarda la respuesta tal y como la produjo el endpoint, sin compresión ni cabeceras de capas exteriores.
