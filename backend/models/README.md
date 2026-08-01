# models/

Entidades ORM — capa de persistencia del backend.

## Responsabilidad

- Definir las entidades declarativas de SQLAlchemy (tablas, columnas, relaciones, índices), heredando de la `Base` declarativa definida en `backend/database/`.
- Cumplir las convenciones de nombres, claves primarias (UUID) y columnas de auditoría obligatorias definidas en [DATABASE-STANDARD.md](../../docs/standards/DATABASE-STANDARD.md).

## Qué NO debe contener

- Lógica de negocio (pertenece a `services/`).
- Serialización de API (eso corresponde a `schemas/`) — un `model` nunca se expone directamente como respuesta HTTP.

## Principio rector

Los `models/` representan la estructura de persistencia; los `schemas/` representan el contrato público de la API. Ambos pueden divergir intencionalmente, y esa separación es la que permite evolucionar la base de datos sin romper el contrato de la API (o viceversa).
