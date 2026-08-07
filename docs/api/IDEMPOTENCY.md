# Idempotencia — TEAF

Reintentos seguros de operaciones no idempotentes (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

## 1. El problema

Un cliente envía `POST /pedidos`. El servidor lo procesa correctamente, pero la respuesta se pierde por un corte de red. El cliente, que no sabe si llegó, reintenta.

Sin idempotencia, se crean **dos pedidos**. Y el cliente no tiene forma de saberlo: recibió un error en el primer intento y un éxito en el segundo.

Con idempotencia, el segundo intento devuelve *exactamente* la respuesta del primero, sin volver a ejecutar el endpoint.

## 2. Las tres reglas

Las tres son necesarias para que la solución sea correcta.

### La clave la pone el cliente

`Idempotency-Key` viaja como cabecera. Solo el cliente sabe qué dos peticiones son "la misma intención de negocio" — el servidor no puede deducirlo, porque dos pedidos idénticos del mismo cliente pueden ser legítimamente dos pedidos.

```http
POST /pedidos HTTP/1.1
Idempotency-Key: pedido-a3f9c21b
Content-Type: application/json

{"sku": "TORUS-100", "cantidad": 2}
```

### La huella la pone el servidor

TEAF calcula un SHA-256 de **método + ruta + cuerpo**. Reutilizar una clave con un cuerpo distinto no es un reintento: es un error del cliente, y devolver la respuesta antigua lo ocultaría. De ahí el `409 Conflict`:

```json
{
  "type": "https://teaf.torus/errors/idempotency-conflict",
  "title": "IdempotencyConflictException",
  "status": 409,
  "detail": "La clave de idempotencia 'pedido-a3f9c21b' ya se usó con una petición distinta. Usa una clave nueva para una petición nueva."
}
```

Se usa SHA-256 y no un hash rápido no criptográfico porque una colisión aquí significaría devolverle a un cliente la respuesta de **otra** petición. El coste de calcularlo es irrelevante comparado con esa consecuencia.

### Solo se guardan respuestas que no sean 5xx

Cachear un `500` condenaría al cliente a recibir ese mismo error durante todo el TTL, incluso cuando la causa ya estuviera resuelta. Un `400`, en cambio, **sí** se guarda: es determinista, y reintentar la misma petición dará el mismo `400`.

## 3. Qué métodos cubre

Por defecto, `POST` y `PATCH`. `GET`, `PUT` y `DELETE` ya son idempotentes por definición de HTTP: repetirlos no cambia el resultado, así que no necesitan esta protección.

```python
from teaf.api import IdempotencyManager

gestor = IdempotencyManager(
    ttl_seconds=86_400,
    methods=("POST", "PATCH"),
    header_name="Idempotency-Key",
)
```

## 4. Respuesta reproducida

Una respuesta reproducida es byte a byte la original (mismo código, mismo cuerpo, mismas cabeceras), más una cabecera que lo declara:

```
X-Idempotent-Replay: true
```

La [auditoría](AUDIT.md) la registra con desenlace `replayed` en lugar de `accepted`, así que el registro distingue las ejecuciones reales de las reproducciones.

## 5. Por qué es el middleware más interno

`IdempotencyMiddleware` va pegado al endpoint, por dentro de compresión, versionado y todo lo demás. La respuesta que guarda debe ser la que produjo el *handler*, sin compresión aplicada ni cabeceras añadidas por capas exteriores: guardar una respuesta ya comprimida obligaría a reproducirla comprimida incluso a un cliente que no admita esa codificación.

Como efecto secundario, el middleware lee el cuerpo de la petición para calcular la huella y lo **repone** en el `receive` de la petición — sin eso, todo endpoint con cuerpo detrás de este middleware recibiría un cuerpo vacío.

## 6. Persistencia y TTL

`IdempotencyManager` usa `InMemoryIdempotencyStore` por defecto, con TTL de 24 h. El TTL debe ser al menos tan largo como la ventana de reintentos de los clientes: si un cliente reintenta al día siguiente y el registro ya expiró, se ejecuta la operación de nuevo.

**Con varias instancias**, un cliente puede reintentar contra una réplica distinta de la que atendió el intento original y la deduplicación falla. Para un despliegue multi-instancia, la idempotencia necesita un almacén compartido.

`RedisIdempotencyStore` (`teaf.api`) lo deja preparado: `SET ... PX ... NX` convierte "reservar la clave" en una operación atómica entre instancias, cerrando además la ventana en la que dos peticiones idempotentes **simultáneas** podrían ejecutarse ambas. Sin conexión real hasta que un ADR apruebe `redis-py` — ver [API-PROTECTION.md](API-PROTECTION.md), §10.

## 7. Configuración por entorno

```bash
API_IDEMPOTENCY_ENABLED=true
API_IDEMPOTENCY_TTL_SECONDS=86400
API_IDEMPOTENCY_HEADER=Idempotency-Key
API_IDEMPOTENCY_METHODS="POST,PATCH"
```

Viene **desactivada** por defecto: activarla cambia el comportamiento observable de una API existente (un reintento deja de crear un recurso nuevo), así que debe ser una decisión explícita.

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa y el orden de la cadena.
- [`examples/idempotent-requests/`](../../examples/idempotent-requests/) — ejemplo ejecutable.
