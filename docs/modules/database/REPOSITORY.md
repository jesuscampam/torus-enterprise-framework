# Repository Pattern — TEAF

`SQLAlchemyRepository` (`backend/providers/database/sqlalchemy_repository.py`), la implementación funcional de `RepositoryBase` (`repository_base.py`, andamiaje de Sprint 2.2) sobre SQLAlchemy 2.x. Ver [DATABASE.md](DATABASE.md) para dónde encaja en el módulo completo.

## 1. Contrato

```python
class SQLAlchemyRepository(RepositoryBase[TModel], Generic[TModel]):
    def __init__(self, session: AsyncSession, model: type[TModel]) -> None: ...

    async def get_by_id(self, entity_id: UUID) -> TModel | None: ...
    async def list_paginated(self, *, page: int, page_size: int) -> list[TModel]: ...
    async def list_filtered(
        self, *, page: int = 1, page_size: int = 20, filters: Mapping[str, object] | None = None
    ) -> list[TModel]: ...
    async def count(self, *, filters: Mapping[str, object] | None = None) -> int: ...
    async def add(self, entity: TModel) -> TModel: ...
    async def update(self, entity: TModel) -> TModel: ...
    async def delete(self, entity_id: UUID) -> None: ...
```

`TModel = TypeVar("TModel", bound=AuditMixin)` — a diferencia del `T` sin cota de `contracts/repository.py` (deliberado allí, para no acoplar `contracts/` a ningún ORM), aquí sí se exige `AuditMixin`: este repositorio ya sabe que opera sobre modelos SQLAlchemy con columnas de auditoría (`id`, `created_at`, `updated_at`, `deleted_at`).

## 2. Construcción — siempre sobre una sesión ya abierta

`session` es una `AsyncSession` real, normalmente `unit_of_work.session` — **nunca** una nueva sesión creada por su cuenta:

```python
async with uow_factory.create() as uow:
    repo = SQLAlchemyRepository(uow.session, Account)
    await repo.add(Account(id=uuid4(), name="acme"))
    await uow.commit()
```

El repositorio no decide su propia frontera transaccional; eso lo delimita quien lo construye (normalmente el Unit of Work — ver [UNIT-OF-WORK.md](UNIT-OF-WORK.md)).

## 3. `flush()`, nunca `commit()`

Ningún método de `SQLAlchemyRepository` llama a `commit()` — solo `flush()` (visibilidad dentro de la misma transacción, sin persistirla). Esto cumple [DATABASE-STANDARD.md, sección 7](../../standards/DATABASE-STANDARD.md#7-transacciones): *"`repository/` no hace `commit()` por su cuenta"*. Verificado explícitamente en `tests/unit/test_db_repository.py::test_repository_never_commits_only_flushes`: sin `uow.commit()`, una segunda sesión no ve los cambios.

## 4. Soft delete — nunca `DELETE` físico

`delete(entity_id)` marca `deleted_at = datetime.now(UTC)` en lugar de eliminar la fila, cumpliendo [DATABASE-STANDARD.md, sección 4](../../standards/DATABASE-STANDARD.md#4-columnas-de-auditoría-obligatorias). Es idempotente: si `entity_id` no existe (o ya estaba borrado), no lanza. Todo método de lectura (`get_by_id`, `list_filtered`, `count`) filtra `deleted_at IS NULL` automáticamente vía `_apply_filters` — nunca hace falta añadir ese filtro a mano.

## 5. Paginación y filtros

`list_paginated(page, page_size)` delega en `list_filtered(page=page, page_size=page_size)` sin filtros — son el mismo camino de código. `list_filtered` acepta `filters: Mapping[str, object]`, un mapa `{nombre_de_columna: valor}` de **igualdad simple** (sin operadores de comparación, sin joins) — "filtros básicos", tal como pide el Sprint 2.6. Los resultados se ordenan siempre por `created_at` antes de paginar, para un orden estable.

`count(filters=...)` aplica el mismo `_apply_filters` que `list_filtered`, así que un `count()` y un `list_filtered()` con los mismos `filters` siempre son coherentes entre sí.

## 6. Extender con un repositorio propio

Un módulo real (fuera de TEAF) que necesite consultas más allá de CRUD/paginación/filtros de igualdad hereda de `SQLAlchemyRepository` y añade métodos propios sobre `self._raw_session`/`self._model` — nunca reimplementa el andamiaje de auditoría o soft delete desde cero. Ver `/templates/repository-template.md` para el patrón general (independiente de esta implementación concreta).

## 7. Qué NO ofrece

Sin `joinedload`/`selectinload` automático (a decidir por cada repositorio concreto según [DATABASE-STANDARD.md, sección 10](../../standards/DATABASE-STANDARD.md#10-prácticas-prohibidas)), sin operadores de filtro más allá de igualdad (`>`, `LIKE`, `IN`...), sin bulk operations, sin caché. Deliberadamente mínimo — "tres líneas similares son preferibles a una abstracción prematura" (CLAUDE.md, sección 3).
