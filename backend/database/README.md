# database/

Infraestructura de acceso a base de datos: motor, sesión y ciclo de vida de la conexión con **PostgreSQL** vía **SQLAlchemy** (ver [ADR-002](../../docs/architecture/adr/ADR-002-uso-de-postgresql.md)).

## Responsabilidad

- Configuración del `engine` de SQLAlchemy y del pool de conexiones (parámetros resueltos desde `backend/config/`, nunca hardcodeados).
- Definición de la `Base` declarativa de la que heredan todos los `models/`.
- Gestión de sesiones (creación, scope por petición, cierre) expuesta como dependencia inyectable a través de `core/`.
- Punto de integración con **Alembic** para las migraciones versionadas en `database/migrations/` (carpeta raíz del repositorio, no confundir con este directorio).

## Qué NO debe contener

- Definiciones de entidades de negocio (eso vive en `models/`).
- Lógica de negocio o de aplicación.

## Relación con `database/` (raíz del repositorio)

Este directorio (`backend/database/`) contiene el **código** de acceso a la base de datos consumido por la aplicación. La carpeta `database/` en la raíz del repositorio contiene los **artefactos de infraestructura de datos** (migraciones Alembic y datos semilla), compartidos potencialmente entre backend y herramientas de operación.
