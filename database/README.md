# database/

Artefactos de infraestructura de datos del framework: migraciones versionadas y datos semilla, en cumplimiento de [DATABASE-STANDARD.md](../docs/standards/DATABASE-STANDARD.md).

## Diferencia con `backend/database/`

- `backend/database/` contiene el **código** de acceso a datos consumido en tiempo de ejecución por la aplicación (motor, sesión, `Base` declarativa).
- `database/` (esta carpeta, en la raíz) contiene los **artefactos versionados de evolución del esquema** (migraciones Alembic) y los **datos iniciales** (seeds), que son operados tanto por la aplicación como por procesos de CI/CD y operación manual.

## Contenido

| Carpeta | Responsabilidad |
|---|---|
| [`migrations/`](migrations/README.md) | Migraciones Alembic versionadas del esquema de PostgreSQL. |
| [`seeds/`](seeds/README.md) | Datos semilla / fixtures para inicializar un entorno nuevo. |
