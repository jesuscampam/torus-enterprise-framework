# Plantilla — Repository Pattern (`backend/repository/`)

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Código ilustrativo para copiar al implementar acceso a datos real, conforme a [DATABASE-STANDARD.md](../docs/standards/DATABASE-STANDARD.md).

## Cómo usar esta plantilla

1. Define primero la **interfaz** (contrato) — es lo que `services/` conoce.
2. Implementa después la versión concreta con SQLAlchemy — es lo único que conoce el motor de base de datos.
3. Respeta las convenciones de `DATABASE-STANDARD.md`: UUID como PK, `deleted_at` para baja lógica, sin `commit()` propio.

```python
# backend/repository/{{recurso}}_repository.py
#
# Contrato + implementación del Repository Pattern para "{{Recurso}}".

from abc import ABC, abstractmethod
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.{{recurso}} import {{Recurso}}Model


class {{Recurso}}Repository(ABC):
    """Contrato consumido por services/. services/ nunca depende de la implementación concreta."""

    @abstractmethod
    async def get_by_id(self, {{recurso}}_id: UUID) -> {{Recurso}}Model | None: ...

    @abstractmethod
    async def list_paginated(self, page: int, page_size: int) -> list[{{Recurso}}Model]: ...

    @abstractmethod
    async def add(self, entity: {{Recurso}}Model) -> {{Recurso}}Model: ...

    # TODO al implementar: update(), soft_delete() (nunca DELETE físico, ver DATABASE-STANDARD.md)


class SQLAlchemy{{Recurso}}Repository({{Recurso}}Repository):
    """Implementación concreta sobre PostgreSQL. No hace commit(): la transacción
    la gestiona services/ (unit of work)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, {{recurso}}_id: UUID) -> {{Recurso}}Model | None:
        # SELECT explícito, filtrando deleted_at IS NULL por defecto (baja lógica)
        ...

    async def list_paginated(self, page: int, page_size: int) -> list[{{Recurso}}Model]:
        ...

    async def add(self, entity: {{Recurso}}Model) -> {{Recurso}}Model:
        self._session.add(entity)
        await self._session.flush()  # flush, no commit — lo decide services/
        return entity
```

## Qué NO hacer en este archivo

- No hacer `commit()` de la sesión (responsabilidad de `services/`).
- No devolver tipos crudos de la base de datos hacia `api/` (services/ traduce si es necesario).
- No usar `SELECT *`; seleccionar columnas explícitas cuando el caso lo amerite.
