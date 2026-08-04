# api/

Capa de interfaz HTTP del backend. Expone los contratos de la API siguiendo el principio **API First** ([ADR-004](../../docs/architecture/adr/ADR-004-api-first.md)) y el [API-STANDARD.md](../../docs/standards/API-STANDARD.md).

## Responsabilidad

- Definir routers/controladores versionados (`/api/v1/...`).
- Recibir y validar peticiones mediante los contratos de `backend/schemas/`.
- Invocar casos de uso de `backend/services/` y traducir su resultado a una respuesta HTTP.
- Declarar la documentación OpenAPI de cada endpoint (resumen, ejemplos, códigos de error).

## Qué NO debe contener

- Lógica de negocio (pertenece a `backend/services/`).
- Acceso directo a `backend/models/` o a la base de datos.
- Reglas de autorización complejas hardcodeadas (deben delegarse a `backend/security/`).

## Estructura prevista (Versión 1 en adelante)

Organización por versión de API y por dominio de recurso, por ejemplo `api/v1/<recurso>/router.py`, manteniendo cada router enfocado en un único recurso o agregado.
