# migrations/

Migraciones de esquema de base de datos gestionadas con **Alembic** (ver [ADR-002](../../docs/architecture/adr/ADR-002-uso-de-postgresql.md)).

## Responsabilidad

- Registrar cada cambio de esquema como una revisión versionada y reversible, generada a partir de los `models/` definidos en `backend/models/`.
- Ser la única vía autorizada para modificar el esquema de PostgreSQL en cualquier entorno (ver [DATABASE-STANDARD.md](../../docs/standards/DATABASE-STANDARD.md)).

## Estado actual

Solo estructura; la configuración de Alembic y la primera migración se incorporan en la Versión 1 del [roadmap](../../docs/roadmap/ROADMAP.md).
