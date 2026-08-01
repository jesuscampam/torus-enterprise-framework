# ADR-002: Uso de PostgreSQL

## Estado

Aceptado

## Contexto

Las aplicaciones que se construirán sobre TEAF (Inventario TI, Gestor de Incidentes, Portal NOC/SRE, integraciones SAP/Salesforce/Control-M, IA Empresarial) requieren un motor de base de datos relacional único y estándar, capaz de soportar tanto datos transaccionales clásicos como necesidades más avanzadas (documentos semiestructurados, búsqueda vectorial para IA), y compatible con el hosting de POC (Render) y de producción (Azure).

## Problema

¿Qué motor de base de datos relacional debe adoptar TEAF como estándar oficial, considerando el principio Database Agnostic a nivel de dominio pero la necesidad de fijar una implementación concreta a nivel de infraestructura?

## Decisión

Se adopta **PostgreSQL** como motor de base de datos relacional oficial de TEAF.

Motivos determinantes:

- Motor open-source, sin coste de licenciamiento, con soporte empresarial disponible tanto en Render (POC) como en Azure Database for PostgreSQL (producción).
- Soporte nativo de tipos avanzados (`JSONB`, `UUID`, arrays) que reducen la necesidad de tablas auxiliares para datos semiestructurados.
- Extensión `pgvector`, que habilita búsqueda por similitud vectorial directamente en la base de datos relacional — clave para el principio AI Ready (RAG, búsqueda semántica) sin introducir un motor de base de datos adicional.
- Cumplimiento ACID completo, imprescindible para dominios de negocio críticos como incidentes, inventario o integraciones financieras/SAP.
- Comunidad y ecosistema de herramientas maduro (SQLAlchemy, Alembic, extensiones de monitoreo).

## Consecuencias

### Positivas

- Una única tecnología de persistencia relacional que cubre casos transaccionales, semiestructurados y de IA, reduciendo la superficie de infraestructura a mantener.
- Migración fluida entre entornos (Render → Azure) al tratarse del mismo motor, sin reescritura de queries específicas de proveedor.
- Base sólida para futuras necesidades analíticas (particionado, índices avanzados) sin cambiar de motor.

### Negativas / Trade-offs

- El equipo debe evitar apoyarse en extensiones o sintaxis exclusivas de PostgreSQL fuera de la capa `repository/`/`database/`, para no violar el principio Database Agnostic a nivel de dominio.
- El uso de `pgvector` introduce una dependencia adicional de extensión que debe gestionarse explícitamente en las migraciones (`database/migrations/`) y en la infraestructura de despliegue.
- Requiere una estrategia explícita de backup/restore y alta disponibilidad en producción (a definir en la Versión 5 del roadmap, hardening empresarial).
