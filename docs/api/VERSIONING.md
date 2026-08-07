# Versionado de API — TEAF

Negociación de la versión de contrato servida en cada petición (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

> No confundir con [docs/public-api/VERSIONING.md](../public-api/VERSIONING.md), que versiona la **API pública de Python** del framework (`teaf.*`). Este documento versiona el **contrato HTTP** de las aplicaciones construidas sobre él.

## 1. Las tres estrategias

TEAF implementa las tres formas habituales de declarar versión, y no impone ninguna.

| Estrategia | Ejemplo | A favor | En contra |
|---|---|---|---|
| **URI** | `GET /api/v2/orders` | La más visible; trivial de enrutar en un balanceador o un gateway. | Ensucia la URL del recurso: el mismo pedido tiene dos URLs. |
| **Cabecera** | `X-API-Version: 2` | URL limpia; trivial de fijar en un cliente. | Invisible desde un navegador; fácil de olvidar al depurar. |
| **Tipo de medio** | `Accept: application/vnd.teaf.v2+json` | La más fiel a HTTP; convive con la negociación de contenido. | La más incómoda de escribir a mano. |

Ninguna es "la correcta". Que un framework las implemente las tres y deje la elección —o la combinación— a cada aplicación es justo lo que debe hacer.

```python
from teaf.api import ApiVersion, ApiVersioningPolicy, ApiVersionNegotiator, VersioningStrategy

negociador = ApiVersionNegotiator(
    ApiVersioningPolicy(
        supported=(ApiVersion(1), ApiVersion(2)),
        default=ApiVersion(1),
        strategies=(VersioningStrategy.URI, VersioningStrategy.HEADER, VersioningStrategy.MEDIA_TYPE),
        header_name="X-API-Version",
        media_type_vendor="teaf",
        strict=True,
    )
)
```

El **orden** de `strategies` es el orden de prioridad: la primera que encuentre una versión gana. Con URI antes que cabecera, `/api/v2/orders` con `X-API-Version: 1` sirve la v2.

## 2. Formato de versión

`ApiVersion.parse()` acepta `"v1"`, `"1"`, `"V2"`, `"v2.1"` y `"3.0"`. `str(ApiVersion(1))` devuelve `"v1"`, y `str(ApiVersion(1, 2))` devuelve `"v1.2"` — el `.0` no se escribe.

`ApiVersion` es ordenable (`ApiVersion(1) < ApiVersion(2)`), que es lo que permite comparar y seleccionar versiones sin escribir comparaciones a mano.

## 3. Anclaje de la versión en la URI

La versión debe ser un **segmento completo** de la ruta: `/api/v2/orders` sí, `/services/v2ray` no. Sin ese anclaje, cualquier identificador que empiece por `v` seguido de dígitos se confundiría con una declaración de versión.

## 4. Versión no soportada

`strict` decide qué ocurre cuando el cliente pide una versión que no se sirve:

- **`True` (por defecto)**: `400 Bad Request` con cuerpo RFC 7807 y la lista de versiones disponibles. Es el valor por defecto porque servir la v1 a quien pidió la v3 produce errores mucho más difíciles de diagnosticar que un rechazo explícito — el cliente recibe datos con la forma equivocada y lo descubre mucho más tarde.
- **`False`**: se cae silenciosamente a `default`.

```json
{
  "type": "https://teaf.torus/errors/unsupported-api-version",
  "title": "UnsupportedApiVersionException",
  "status": 400,
  "detail": "La versión de API '9' no está soportada. Versiones disponibles: v1, v2.",
  "instance": "/api/v9/orders"
}
```

## 5. Deprecación y retirada

```python
ApiVersioningPolicy(
    supported=(ApiVersion(1), ApiVersion(2)),
    default=ApiVersion(2),
    deprecated={"v1": "Wed, 31 Dec 2026 23:59:59 GMT"},
)
```

Una versión obsoleta **se sigue sirviendo**, pero cada respuesta lleva:

| Cabecera | Valor |
|---|---|
| `Deprecation` | `true` |
| `Sunset` | La fecha declarada (RFC 8594) |

Son las cabeceras estándar de retirada: avisan sin romper a nadie todavía, y dan a los clientes una fecha concreta contra la que planificar.

## 6. Qué hace y qué no hace el middleware

**Hace**: resolver la versión, validarla contra las soportadas, dejarla en `request.state.api_version` y comunicarla en la respuesta (`X-API-Version`, más `Deprecation`/`Sunset` si aplica). También la incluye en cada entrada de [auditoría](AUDIT.md).

**No hace**: enrutar. Elegir qué implementación atiende cada versión —dos routers, una rama en el servicio, dos despliegues distintos— es una decisión de la aplicación, y un framework que la impusiera limitaría más de lo que ayuda.

```python
from fastapi import Request

@app.get("/api/v1/orders")
@app.get("/api/v2/orders")
def orders(request: Request) -> dict[str, object]:
    negociacion = request.state.api_version
    if negociacion.version.major >= 2:
        return {"data": [...], "meta": {...}}     # contrato v2
    return {"orders": [...]}                       # contrato v1
```

## 7. Configuración por entorno

```bash
API_VERSIONING_ENABLED=true
API_VERSIONING_SUPPORTED="v1,v2"
API_VERSIONING_DEFAULT=v1
API_VERSIONING_STRATEGIES="uri,header,media_type"
API_VERSIONING_HEADER=X-API-Version
API_VERSIONING_MEDIA_TYPE_VENDOR=teaf
API_VERSIONING_STRICT=true
```

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa.
- [API-STANDARD.md](../standards/API-STANDARD.md) — el estándar de diseño de APIs de TEAF.
- [`examples/api-versioning/`](../../examples/api-versioning/) — ejemplo ejecutable.
