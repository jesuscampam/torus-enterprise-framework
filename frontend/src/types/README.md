# types/

Tipos e interfaces TypeScript compartidos entre múltiples módulos del frontend.

## Responsabilidad

- Tipos que reflejan los contratos de `backend/schemas/` consumidos por `services/` (request/response de la API).
- Tipos de dominio de UI compartidos entre varios componentes o páginas.

## Qué NO debe contener

- Tipos usados por un único componente o página (deben declararse localmente junto a su uso).

## Principio rector

Los tipos de esta carpeta deben mantenerse alineados con los `schemas/` del backend; un cambio de contrato de API (ver [API-STANDARD.md](../../../docs/standards/API-STANDARD.md)) implica actualizar los tipos correspondientes aquí.
