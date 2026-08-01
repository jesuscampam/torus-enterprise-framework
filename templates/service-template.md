# Plantilla — Caso de uso (`backend/services/`)

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Código ilustrativo para copiar al implementar un caso de uso real, conforme a [ARCHITECTURE.md](../docs/architecture/ARCHITECTURE.md) (Service Layer).

## Cómo usar esta plantilla

1. El servicio orquesta uno o más `repository/`; nunca contiene SQL ni detalles HTTP.
2. Gestiona el límite de la transacción (unit of work) cuando la operación toca más de una entidad.
3. Debe poder probarse unitariamente sustituyendo el repositorio por un doble de prueba (mock/fake).

```python
# backend/services/{{recurso}}_service.py
#
# Caso de uso para "{{Recurso}}". Orquesta repository/, aplica reglas de negocio
# y traduce errores de dominio a excepciones de core/.

from backend.core.exceptions import NotFoundError
from backend.repository.{{recurso}}_repository import {{Recurso}}Repository
from backend.schemas.{{recurso}} import {{Recurso}}CreateSchema, {{Recurso}}ResponseSchema


class {{Recurso}}Service:
    def __init__(self, repository: {{Recurso}}Repository) -> None:
        # Se inyecta la INTERFAZ del repositorio, nunca la implementación concreta.
        self._repository = repository

    async def create(self, payload: {{Recurso}}CreateSchema) -> {{Recurso}}ResponseSchema:
        # Aquí van las reglas de negocio que dependen de estado (no de forma,
        # que ya validó el schema en la capa api/).
        entity = payload.to_model()  # traducción schema -> model, ilustrativa
        created = await self._repository.add(entity)
        return {{Recurso}}ResponseSchema.from_model(created)

    async def list_paginated(self, page: int, page_size: int) -> list[{{Recurso}}ResponseSchema]:
        entities = await self._repository.list_paginated(page, page_size)
        return [{{Recurso}}ResponseSchema.from_model(e) for e in entities]

    async def get_or_raise(self, {{recurso}}_id) -> {{Recurso}}ResponseSchema:
        entity = await self._repository.get_by_id({{recurso}}_id)
        if entity is None:
            raise NotFoundError(f"{{Recurso}} con id {{{recurso}}_id} no encontrado")
        return {{Recurso}}ResponseSchema.from_model(entity)

    # TODO al implementar: métodos que requieran orquestar más de un repositorio
    # dentro de una única transacción (unit of work explícito).
```

## Qué NO hacer en este archivo

- No importar nada de `fastapi` ni manejar códigos de estado HTTP (eso es de `api/`).
- No escribir SQL ni usar la sesión de SQLAlchemy directamente (eso es de `repository/`).
- No revalidar lo que el `schema` de entrada ya garantizó.
