# ADR-001: Uso de FastAPI

## Estado

Aceptado

## Contexto

TEAF necesita un framework backend sobre el cual construir la capa `api/` de todas las aplicaciones empresariales futuras de TORUS. El framework elegido debe soportar de forma nativa el principio **API First** (contratos OpenAPI como fuente de verdad), operar de forma eficiente bajo carga concurrente (integraciones con SAP, Salesforce, Control-M y consumo desde múltiples portales simultáneos), e integrarse de forma natural con el resto de la arquitectura en capas (validación de `schemas/`, inyección de dependencias hacia `services/`).

## Problema

¿Qué framework backend en Python debe adoptar TEAF como estándar oficial para toda la capa de API de las aplicaciones construidas sobre el framework?

## Decisión

Se adopta **FastAPI** como framework backend oficial de TEAF.

Motivos determinantes:

- Generación automática de documentación OpenAPI/Swagger a partir del propio código, alineado directamente con el principio API First.
- Soporte nativo de `async`/`await` sobre ASGI, necesario para escalar integraciones I/O-intensivas (SAP, Salesforce, Control-M, llamadas a modelos de IA).
- Validación de datos de entrada/salida basada en Pydantic, el mismo mecanismo que se usa para los `schemas/` de TEAF, evitando una capa de validación duplicada.
- Sistema de inyección de dependencias integrado, compatible con el principio de Dependency Injection del framework.
- Rendimiento comparable a frameworks Node.js/Go, superior a alternativas WSGI síncronas como Django o Flask clásico.

## Consecuencias

### Positivas

- Los contratos de API se mantienen siempre sincronizados con la implementación (no hay documentación que se desactualice manualmente).
- Reducción de código repetitivo de validación gracias a Pydantic compartido entre `schemas/` y el framework web.
- Curva de entrada baja para desarrolladores con experiencia en Python moderno (type hints).
- Facilita el testing de la capa `api/` de forma aislada mediante el sistema de dependencias inyectables.

### Negativas / Trade-offs

- Ecosistema de terceros (plugins, extensiones) menos extenso que Django, por lo que TEAF debe proveer directamente ciertas piezas (middlewares de seguridad, paginación estándar) en sus propias capas (`middleware/`, `shared/`).
- Al no imponer una estructura de proyecto por defecto, la disciplina de capas (Clean Architecture) recae enteramente en las convenciones de TEAF, no en el framework; se mitiga documentando y exigiendo la estructura en `docs/architecture/ARCHITECTURE.md` y `docs/standards/CODING-STANDARD.md`.
- Requiere que todo el equipo interiorice programación asíncrona correctamente para evitar bloqueos accidentales del event loop.
