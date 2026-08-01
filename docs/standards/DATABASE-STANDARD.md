# Estándar de Base de Datos — TEAF

Este documento define las convenciones obligatorias de modelado, acceso y evolución de la base de datos para cualquier aplicación construida sobre TEAF, en cumplimiento del principio **Database Agnostic** y del stack oficial (PostgreSQL + SQLAlchemy + Alembic, ver [ADR-002](../architecture/adr/ADR-002-uso-de-postgresql.md)).

## 1. Database Agnostic a nivel de dominio

- `services/` y capas superiores no contienen SQL ni conocen detalles del motor de base de datos; toda interacción pasa por `repository/`.
- Las características específicas de PostgreSQL (JSONB, arrays, `pgvector`) se encapsulan dentro de `database/` y `repository/`; nunca se filtran como tipos de retorno hacia `services/` sin traducción a tipos de dominio.

## 2. Convenciones de nombres

- Tablas: sustantivos en plural, `snake_case` (`incidents`, `ticket_comments`).
- Columnas: `snake_case` (`created_at`, `assigned_to_id`).
- Claves foráneas: `<entidad_singular>_id` (`incident_id`, `user_id`).
- Tablas de relación muchos-a-muchos: `<entidad_a>_<entidad_b>` en singular u orden alfabético consistente (`incident_tag`).
- Índices: `ix_<tabla>_<columna(s)>`. Constraints únicos: `uq_<tabla>_<columna(s)>`. Claves foráneas: `fk_<tabla>_<columna>_<tabla_referenciada>`.

## 3. Claves primarias

- Toda tabla usa **UUID** como clave primaria (`id UUID PRIMARY KEY DEFAULT gen_random_uuid()`), nunca enteros autoincrementales, para evitar colisiones al integrar datos entre aplicaciones/entornos (Render, Azure) y no filtrar volumetría de negocio a través de IDs secuenciales expuestos en la API.

## 4. Columnas de auditoría obligatorias

Toda tabla de negocio incluye como mínimo:

| Columna | Tipo | Descripción |
|---|---|---|
| `created_at` | `timestamptz` | Fecha de creación, asignada por la base de datos (`server_default=now()`). |
| `updated_at` | `timestamptz` | Fecha de última modificación, actualizada automáticamente. |
| `deleted_at` | `timestamptz`, nullable | Marca de baja lógica (soft delete). `NULL` = registro activo. |

- Se prohíbe el `DELETE` físico de registros de negocio salvo requisitos explícitos de cumplimiento normativo (a documentar caso por caso); la baja se realiza mediante `deleted_at`.
- Los repositorios filtran por `deleted_at IS NULL` por defecto en toda consulta estándar.

## 5. Migraciones (Alembic)

- Todo cambio de esquema se realiza exclusivamente mediante migraciones de Alembic versionadas en `database/migrations/`; se prohíbe modificar el esquema manualmente en cualquier entorno.
- Las migraciones autogeneradas (`alembic revision --autogenerate`) se revisan manualmente antes de aplicarse: Alembic no detecta de forma fiable cambios de tipo, renombrados de columna, ni ciertos constraints.
- Cada migración debe ser reversible (`downgrade()` implementado), salvo que la irreversibilidad sea intencional y esté documentada en el mensaje de la migración.
- Las migraciones que afectan a tablas con volumen significativo de datos deben evaluarse por impacto de bloqueo (locking) y, si es necesario, dividirse en pasos compatibles con despliegue sin downtime (expand/contract pattern).

## 6. Indexación

- Toda clave foránea lleva un índice explícito.
- Toda columna usada habitualmente en filtros de `WHERE` o `ORDER BY` en consultas de `repository/` debe evaluarse para indexación.
- Los índices se definen en el propio modelo SQLAlchemy y se versionan junto con la migración que los crea.

## 7. Transacciones

- Toda operación que modifique más de una tabla se ejecuta dentro de una única transacción gestionada por `services/` (unit of work), nunca se dejan múltiples `commit()` parciales dentro de un mismo caso de uso.
- `repository/` no hace `commit()` por su cuenta; expone operaciones que participan en la transacción gestionada por la capa de servicio.

## 8. Pooling de conexiones

- La configuración del pool de conexiones (tamaño mínimo/máximo, timeout, reciclado) se resuelve vía `backend/config/` por entorno, nunca hardcodeada en `database/`.
- El tamaño del pool debe dimensionarse considerando el número de instancias horizontalmente escalables (principio Cloud Ready) para no agotar las conexiones máximas de PostgreSQL.

## 9. Multi-tenancy y aislamiento de datos

- Si una aplicación requiere aislamiento por tenant/organización, se modela mediante una columna `tenant_id` indexada y filtrada de forma transversal en `repository/`, nunca mediante bases de datos o esquemas separados por defecto (salvo justificación explícita documentada como ADR).

## 10. Prácticas prohibidas

- SQL embebido directamente en `services/` o `api/`.
- Uso de `SELECT *` en código de producción; se seleccionan explícitamente las columnas necesarias.
- Consultas N+1 no evaluadas: toda relación cargada en bucle debe justificar `joinedload`/`selectinload` explícito en `repository/`.
- Credenciales de base de datos en el código fuente o en archivos versionados; se gestionan vía `config/` y secretos de entorno (ver `SECURITY-STANDARD.md`).
