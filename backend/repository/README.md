# repository/

Implementación del **Repository Pattern**: abstrae el acceso a datos detrás de interfaces estables.

## Responsabilidad

- Definir interfaces (contratos) de acceso a datos consumidas por `services/`.
- Proveer implementaciones concretas basadas en SQLAlchemy sobre `database/` y `models/`.
- Traducir entre entidades de persistencia (`models/`) y objetos de dominio cuando sea necesario.
- Encapsular cualquier particularidad del motor de base de datos (PostgreSQL), en cumplimiento del principio Database Agnostic — ver [DATABASE-STANDARD.md](../../docs/standards/DATABASE-STANDARD.md).

## Qué NO debe contener

- Lógica de negocio (pertenece a `services/`).
- `commit()` de transacciones que abarcan más de una operación — la gestión de la transacción es responsabilidad de `services/`.

## Principio rector

`services/` depende de la **interfaz** del repositorio, nunca de su implementación concreta con SQLAlchemy; esto permite sustituir la implementación (otro motor, un doble de prueba) sin tocar la capa de aplicación.
