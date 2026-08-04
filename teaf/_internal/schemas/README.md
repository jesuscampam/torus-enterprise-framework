# schemas/

Contratos de entrada y salida de la API — DTOs basados en **Pydantic**.

## Responsabilidad

- Definir los payloads de request y response de cada endpoint de `api/`, en cumplimiento de [API-STANDARD.md](../../docs/standards/API-STANDARD.md).
- Validar la forma y los tipos de los datos de entrada antes de que lleguen a `services/`.
- Servir como fuente de la documentación OpenAPI generada automáticamente por FastAPI (principio API First).

## Qué NO debe contener

- Lógica de negocio ni de persistencia.
- Referencias directas a `models/` de SQLAlchemy (los schemas se mapean explícitamente, no se reutiliza el modelo ORM como contrato de API).

## Principio rector

Un `schema` es un contrato público y versionado; un cambio incompatible en un schema es un cambio incompatible de API y debe tratarse según la política de versionado de [API-STANDARD.md](../../docs/standards/API-STANDARD.md).
