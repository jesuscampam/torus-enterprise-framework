# shared/

Utilidades, constantes y tipos genéricos reutilizables entre capas del backend.

## Responsabilidad

- Funciones auxiliares puras y de propósito general (formateo, manejo de fechas, validaciones genéricas) sin dependencia de una capa de negocio concreta.
- Constantes compartidas (por ejemplo, valores por defecto de paginación) usadas por más de una capa.
- Tipos y estructuras de datos genéricas reutilizadas por `services/`, `repository/` o `api/`.

## Qué NO debe contener

- Lógica de negocio de un dominio específico.
- Dependencias hacia capas superiores como `api/` o `services/` — `shared/` es consumido, nunca consumidor de lógica de negocio.

## Principio rector

Si una utilidad empieza a acumular conocimiento de negocio específico de una aplicación, ya no pertenece a `shared/`: debe moverse a la capa de dominio correspondiente (`services/` o `models/`).
