# integration/

Pruebas de integración: verifican la interacción real entre capas (por ejemplo, `services/` operando sobre `repository/` contra una base de datos PostgreSQL de prueba, típicamente levantada vía Docker).

## Convenciones

- Se permite y se espera el uso de infraestructura real (contenedor de PostgreSQL efímero), nunca contra una base de datos compartida de desarrollo o producción.
- Cubren especialmente los flujos de `api/` que involucran autenticación (`security/`), validación de `schemas/` y persistencia real.
