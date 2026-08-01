# services/

Capa de aplicación (Service Layer). Aquí vive la lógica de casos de uso.

## Responsabilidad

- Orquestar uno o más `repository/` para ejecutar un caso de uso completo.
- Aplicar reglas de negocio y validaciones que dependen de estado (no solo de forma, que ya valida `schemas/`).
- Gestionar los límites de transacción (unit of work) cuando una operación afecta a más de una entidad.
- Traducir errores de dominio en excepciones definidas en `core/`, consumidas después por `api/`.

## Qué NO debe contener

- Detalles HTTP (códigos de estado, headers) — eso pertenece a `api/`.
- SQL o detalles de persistencia — eso pertenece a `repository/` y `database/`.
- Dependencias directas de frameworks web.

## Principio rector

Un servicio debe poder probarse unitariamente sustituyendo sus repositorios por dobles de prueba (mocks/fakes), sin levantar una base de datos real ni un servidor HTTP.
