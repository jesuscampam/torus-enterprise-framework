"""Database Module — Sprint 2.6 (Enterprise Persistence Foundation).

Primer módulo oficial de TEAF construido enteramente sobre el Module SDK
(``backend/sdk/``, Sprint 2.5): ``DatabaseModule`` hereda de ``ModuleBase``
y no llama directamente a ninguna pieza del ``ServiceContainer`` ni del
``CapabilityRegistry`` — todo se declara en ``DatabaseManifest`` y el SDK lo
registra automáticamente.

Este paquete es la capa de **ensamblado** (usa el SDK, construye el motor
SQLAlchemy a partir de configuración, expone health checks); la
implementación concreta de SQLAlchemy vive en ``backend/providers/database/``
(``SQLAlchemyDatabaseProvider``, ``SQLAlchemyRepository``,
``SQLAlchemyUnitOfWork``, ...) — ``backend/modules/database/`` depende de
``backend/providers/database/``, nunca al revés.

Sin entidades ni tablas de negocio: solo infraestructura de persistencia
reutilizable por cualquier aplicación futura construida sobre TEAF.
"""
