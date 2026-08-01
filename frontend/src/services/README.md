# services/

Capa de cliente API — único punto de comunicación HTTP con el backend.

## Responsabilidad

- Encapsular las llamadas HTTP tipadas hacia `backend/api/`, alineadas con los contratos definidos en [API-STANDARD.md](../../../docs/standards/API-STANDARD.md).
- Manejar la adjunción del token JWT y la renovación de sesión (en coordinación con `store/`).
- Traducir errores de API (formato RFC 7807) a un formato consumible por la UI.

## Qué NO debe contener

- Lógica de presentación o de componente.

## Principio rector

Ningún componente ni página realiza `fetch`/`axios` directamente; siempre pasa por esta capa, de forma equivalente al Repository Pattern del backend.
