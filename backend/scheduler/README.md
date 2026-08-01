# scheduler/

Framework de tareas programadas y trabajos en background.

## Responsabilidad

- Definir la abstracción de tareas recurrentes (cron) y diferidas (jobs en cola) consumida por `services/`.
- Garantizar coordinación segura entre múltiples instancias de la aplicación (principio Cloud Ready, [ADR-005](../../docs/architecture/adr/ADR-005-cloud-ready.md)), evitando ejecuciones duplicadas de un mismo job.
- Registrar el resultado de cada ejecución (éxito, fallo, duración) para observabilidad (`monitoring/`).

## Qué NO debe contener

- Lógica de negocio del job en sí (el job orquesta `services/`, no reimplementa casos de uso).

## Estado actual

Solo estructura; la implementación concreta llega en la Versión 4 del [roadmap](../../docs/roadmap/ROADMAP.md).
