# seeds/

Datos semilla (seed data) para inicializar un entorno nuevo (desarrollo local, POC en Render, entorno de pruebas de CI).

## Responsabilidad

- Conjuntos de datos mínimos y reproducibles necesarios para que una aplicación construida sobre TEAF sea utilizable tras un despliegue nuevo (por ejemplo, roles y permisos base del modelo RBAC).
- Scripts idempotentes: ejecutar un seed más de una vez no debe duplicar datos ni fallar.

## Qué NO debe contener

- Datos de producción reales ni información sensible.
