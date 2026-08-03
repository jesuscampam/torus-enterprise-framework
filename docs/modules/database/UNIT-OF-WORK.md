# Unit of Work — TEAF

`SQLAlchemyUnitOfWork` y `SQLAlchemyUnitOfWorkFactory` (`backend/providers/database/sqlalchemy_unit_of_work.py`), la implementación funcional del contrato `UnitOfWork` (`backend/contracts/unit_of_work.py`, Sprint 2.2). Ver [DATABASE.md](DATABASE.md) para dónde encaja en el módulo completo.

## 1. Contrato

```python
class UnitOfWork(ABC):
    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(self, exc_type, exc_value, traceback) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

`SQLAlchemyUnitOfWork` implementa este contrato sobre una `AsyncSession` propia (una por Unit of Work, nunca compartida). `SQLAlchemyUnitOfWorkFactory(provider)` crea una instancia nueva por cada `.create()`, sobre una sesión recién abierta vía `provider.get_session()` — esto es lo que declara el servicio `UnitOfWork` del manifiesto como `Lifetime.TRANSIENT` en vez de `SINGLETON`: cada resolución del Service Container obtiene su propia transacción aislada.

## 2. El límite de la transacción

```python
async with uow_factory.create() as uow:
    repo = SQLAlchemyRepository(uow.session, Account)
    await repo.add(Account(id=uuid4(), name="acme"))
    await uow.commit()          # ← explícito, obligatorio para persistir
```

`__aenter__` abre la transacción y devuelve el propio `uow`. `__aexit__`:

- Si el bloque `async with` termina por una excepción, hace `rollback()` automáticamente antes de cerrar la sesión.
- Si termina limpio (sin excepción), **no hace `commit()` implícito** — cierra la sesión sin persistir nada que no se haya confirmado explícitamente con `await uow.commit()`.

Este es el contrato central verificado por `tests/unit/test_db_unit_of_work.py::test_uow_never_auto_commits_on_clean_exit`: salir del bloque sin llamar a `commit()` no persiste los cambios, aunque no haya habido ningún error.

## 3. Por qué "nunca commit implícito"

[DATABASE-STANDARD.md, sección 7](../../standards/DATABASE-STANDARD.md#7-transacciones) exige que toda operación que modifique más de una tabla se ejecute dentro de una única transacción gestionada explícitamente, "nunca se dejan múltiples `commit()` parciales dentro de un mismo caso de uso". Un `commit()` implícito al salir del bloque haría imposible distinguir "terminé con éxito" de "simplemente dejé de escribir código dentro del `with`" — el llamador (normalmente `services/` en una aplicación construida sobre TEAF) siempre decide explícitamente cuándo confirmar.

## 4. Rollback explícito vs. rollback por excepción

Ambos caminos existen y están cubiertos por pruebas independientes:

- **Por excepción**: `raise` dentro del bloque → `__aexit__` revierte automáticamente.
- **Explícito**: `await uow.rollback()` dentro del bloque, sin lanzar — útil cuando la lógica de negocio decide descartar el trabajo sin que eso sea técnicamente un error.

## 5. Integración con el Repository Pattern

Un `SQLAlchemyRepository` se construye siempre sobre `uow.session` (ver [REPOSITORY.md](REPOSITORY.md)) — nunca sobre una sesión independiente. Varios repositorios pueden compartir el mismo `uow` para que sus cambios formen parte de una única transacción:

```python
async with uow_factory.create() as uow:
    accounts = SQLAlchemyRepository(uow.session, Account)
    invoices = SQLAlchemyRepository(uow.session, Invoice)
    await accounts.add(...)
    await invoices.add(...)
    await uow.commit()          # ambos cambios se confirman juntos, o ninguno
```

## 6. Integración con el Service Container

`build_database_manifest` (`manifest.py`) declara `UnitOfWork` como:

```python
.add_service(UnitOfWork, lambda c: uow_factory.create(), lifetime=Lifetime.TRANSIENT, ...)
```

Cualquier código con acceso al `Runtime` obtiene una unidad de trabajo nueva e independiente en cada resolución: `runtime.resolve_service(UnitOfWork)` nunca devuelve la misma instancia dos veces (verificado en `tests/integration/test_database_module_bootstrap.py::test_unit_of_work_service_is_transient_per_resolution`).

## 7. Qué NO ofrece

Sin anidamiento de Unit of Work (savepoints), sin propagación automática de transacción entre llamadas HTTP, sin retry automático ante conflictos de concurrencia. Ese comportamiento, si se necesita, se construye en la capa de `services/` de una aplicación concreta — nunca aquí.
