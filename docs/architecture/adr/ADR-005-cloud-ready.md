# ADR-005: Cloud Ready

## Estado

Aceptado

## Contexto

Las aplicaciones construidas sobre TEAF deben poder desplegarse indistintamente en un hosting de bajo coste para validación (Render) y en la infraestructura empresarial de producción (Azure App Service), y escalar horizontalmente ante picos de carga (por ejemplo, integraciones masivas con Control-M o SAP, o consumo simultáneo desde varios portales). Una arquitectura que asuma estado local en disco, sesión afinizada a una única instancia, o configuración embebida en código, no puede cumplir ese requisito sin reescrituras costosas.

## Problema

¿Qué restricciones arquitectónicas debe imponer TEAF a todas sus capas para garantizar que cualquier aplicación construida sobre el framework sea desplegable y escalable en la nube desde el primer día, sin rediseño posterior?

## Decisión

Se adopta **Cloud Ready** como principio arquitectónico obligatorio, con las siguientes reglas concretas aplicadas de forma transversal:

- **Sin estado en proceso**: ninguna capa (`api/`, `services/`) mantiene estado de sesión en memoria local; la autenticación es stateless vía JWT (ver ADR futuro sobre seguridad) y cualquier estado compartido vive en PostgreSQL o en un almacén externo, nunca en el sistema de archivos del contenedor.
- **Configuration by Environment**: toda credencial, endpoint o flag se resuelve a través de `teaf/_internal/config/` leyendo variables de entorno, nunca hardcodeada.
- **Docker First** (ADR-003) como mecanismo de empaquetado que garantiza portabilidad entre Render y Azure App Service.
- **Observability First**: instrumentación con OpenTelemetry desde el diseño, para poder diagnosticar comportamiento en entornos distribuidos donde no hay acceso directo a la máquina.
- Los componentes de background (`scheduler/`) y de integración (`webhooks/`) se diseñan asumiendo múltiples instancias concurrentes, evitando trabajos que dependan de ejecutarse en una única instancia sin coordinación explícita.

## Consecuencias

### Positivas

- Cualquier aplicación construida sobre TEAF puede escalar horizontalmente en Azure App Service (o migrar de Render a Azure) sin cambios de arquitectura.
- Facilita recuperación ante fallos: al no haber estado local crítico, una instancia puede reiniciarse o reemplazarse sin pérdida de datos.
- Simplifica las pruebas de carga y los despliegues blue-green/canary en producción.

### Negativas / Trade-offs

- Exige diseñar `scheduler/` y `webhooks/` con mecanismos explícitos de coordinación (por ejemplo, locks distribuidos o colas) para evitar ejecuciones duplicadas entre instancias, lo cual añade complejidad frente a un enfoque de instancia única.
- Prohíbe patrones de implementación más simples pero no escalables (por ejemplo, cachés en memoria de proceso sin invalidación distribuida), incluso en fases tempranas donde esa simplicidad sería suficiente.
- Requiere que todo el equipo valide sus decisiones de diseño contra el supuesto de "múltiples instancias, sin afinidad", lo que incrementa la carga cognitiva en el diseño de nuevas capacidades.
