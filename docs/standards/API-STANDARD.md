# Estándar de API — TEAF

Este documento define las convenciones obligatorias para diseñar e implementar cualquier API expuesta por una aplicación construida sobre TEAF, en cumplimiento del principio **API First** (ver [ADR-004](../architecture/adr/ADR-004-api-first.md)).

## 1. Diseño primero, implementación después

El contrato de cada endpoint (ruta, método, payload de entrada, payload de salida, códigos de error) se define antes de implementar la lógica de negocio. El contrato se expresa mediante los `schemas/` (Pydantic) y se materializa automáticamente como especificación OpenAPI.

## 2. Versionado

- Toda API se expone bajo un prefijo de versión explícito: `/api/v1/...`.
- Un cambio **incompatible** (breaking change: eliminar un campo, cambiar un tipo, cambiar el significado de un endpoint) exige una nueva versión (`/api/v2`), nunca se introduce silenciosamente en una versión ya publicada.
- Un cambio **compatible** (añadir un campo opcional, un nuevo endpoint) puede incorporarse dentro de la misma versión.
- Toda versión deprecada se marca explícitamente en la documentación OpenAPI y mantiene un período de convivencia mínimo antes de retirarse.

## 3. Convenciones de nombres y rutas

- Recursos en **plural** y en minúsculas: `/api/v1/incidents`, `/api/v1/tickets`.
- Jerarquía de recursos anidados solo cuando exista una relación de pertenencia real: `/api/v1/incidents/{incident_id}/comments`.
- Verbos HTTP con semántica estricta: `GET` (lectura, sin efectos secundarios), `POST` (creación), `PUT` (reemplazo completo), `PATCH` (actualización parcial), `DELETE` (eliminación o baja lógica).
- No se usan verbos en las rutas (`/api/v1/incidents/close` está prohibido; se modela como `PATCH /api/v1/incidents/{id}` con el cambio de estado en el payload, o como una acción explícita bien justificada `/api/v1/incidents/{id}:close` solo si no existe alternativa RESTful razonable).

## 4. Formato de request / response

- Todo payload de entrada y salida se valida mediante un `schema` de `teaf/_internal/schemas/`, nunca se expone directamente un `model` de `teaf/_internal/models/`.
- Los cuerpos de petición y respuesta usan `camelCase` o `snake_case` de forma **consistente en toda la API** (se define una única convención por proyecto y se documenta en el propio proyecto; el framework no impone cuál, pero prohíbe mezclarlas).
- Las respuestas de colecciones siempre siguen un sobre (envelope) consistente:

```json
{
  "data": [ ... ],
  "meta": {
    "page": 1,
    "pageSize": 20,
    "totalItems": 134,
    "totalPages": 7
  }
}
```

## 5. Paginación, filtrado y orden

- Paginación basada en `page` y `pageSize` como query params estándar (`?page=2&pageSize=20`), con límites máximos configurables por endpoint.
- Filtrado mediante query params explícitos y documentados por endpoint (`?status=open&priority=high`); no se acepta filtrado por lenguaje de query arbitrario sin validación estricta.
- Orden mediante `?sort=field` y `?order=asc|desc`; múltiples criterios se separan por coma (`?sort=priority,createdAt`).

## 6. Formato de errores

Todos los errores siguen el formato **RFC 7807 (Problem Details)**:

```json
{
  "type": "https://teaf.torus/errors/validation-error",
  "title": "Error de validación",
  "status": 422,
  "detail": "El campo 'priority' debe ser uno de: low, medium, high, critical.",
  "instance": "/api/v1/incidents",
  "correlationId": "b3f1c2e4-..."
}
```

- `correlationId` es obligatorio en toda respuesta de error y coincide con el correlation-id generado por `middleware/` (ver `LOGGING-STANDARD.md`), para poder trazar el error en los logs.
- Los mensajes de `detail` no exponen información sensible (stack traces, rutas internas del sistema, detalles de la base de datos).

## 7. Códigos de estado HTTP

| Código | Uso |
|---|---|
| 200 | Operación exitosa con contenido de respuesta. |
| 201 | Recurso creado exitosamente (incluye `Location` header). |
| 204 | Operación exitosa sin contenido de respuesta. |
| 400 | Petición malformada. |
| 401 | No autenticado (token ausente o inválido). |
| 403 | Autenticado pero sin permiso sobre el recurso. |
| 404 | Recurso inexistente. |
| 409 | Conflicto (violación de unicidad, estado inconsistente). |
| 422 | Error de validación de payload. |
| 429 | Límite de tasa excedido. |
| 500 | Error interno no controlado (debe ser excepcional, nunca el camino esperado). |

## 8. Idempotencia

- Los métodos `GET`, `PUT`, `DELETE` deben ser idempotentes por definición.
- Las operaciones `POST` que crean efectos costosos o no repetibles (por ejemplo, disparar una integración con SAP) deben aceptar un header `Idempotency-Key` opcional para evitar duplicados ante reintentos de red.

## 9. Documentación OpenAPI

- Todo endpoint debe declarar: resumen, descripción, `schema` de request/response, y todos los códigos de error posibles con ejemplos.
- Los `schemas/` deben incluir descripciones de campo (`Field(..., description=...)`) que se reflejen automáticamente en la documentación generada.

## 10. Autenticación y seguridad de la API

- Toda ruta protegida exige un JWT válido en el header `Authorization: Bearer <token>`, verificado por `middleware/` antes de llegar a `api/` (ver `SECURITY-STANDARD.md`).
- Las rutas públicas (sin autenticación) deben declararse explícitamente y justificarse; por defecto, toda ruta nueva se considera protegida.

## 11. Rate limiting

- Toda API expone headers estándar de límite de tasa en cada respuesta: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- El límite por defecto se configura vía `config/` (nunca hardcodeado) y puede variar por tipo de cliente (usuario interactivo vs. integración de sistema).
