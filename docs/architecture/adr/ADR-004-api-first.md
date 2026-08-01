# ADR-004: API First

## Estado

Aceptado

## Contexto

TEAF es un framework compartido por múltiples aplicaciones (TicketGateway, Portal TORUS, Portal NOC, Portal SRE, Inventario TI, integraciones SAP/Salesforce/Control-M) y por múltiples consumidores de cada API (frontends propios, integraciones externas, automatizaciones, agentes de IA). Diseñar la API como una consecuencia tardía de la implementación genera contratos inconsistentes, cambios que rompen a consumidores externos, y documentación desactualizada o inexistente.

## Problema

¿Cómo garantiza TEAF que cada API expuesta por las aplicaciones construidas sobre el framework sea consistente, versionada, documentada y estable para múltiples consumidores desde el primer momento?

## Decisión

Se adopta **API First** como principio arquitectónico obligatorio: el contrato de la API (rutas, payloads, códigos de estado, errores) se diseña y valida **antes** de escribir la lógica de negocio que lo implementa, y ese contrato —expresado como especificación OpenAPI generada por FastAPI— es la fuente de verdad para cualquier consumidor.

Implicaciones concretas de la decisión:

- Toda API construida sobre TEAF se rige por `docs/standards/API-STANDARD.md` (versionado, formato de errores, paginación, convenciones de nombres).
- Los `schemas/` (contratos Pydantic) se diseñan antes o junto con el caso de uso en `services/`, nunca se infieren automáticamente desde los `models/` de persistencia.
- Ningún cambio incompatible se introduce en una versión de API ya publicada; requiere una nueva versión (`/api/v2`, etc.).

## Consecuencias

### Positivas

- La documentación de la API (Swagger/OpenAPI) está siempre sincronizada con el código, generada automáticamente por FastAPI (ver ADR-001).
- Los equipos de frontend, integraciones y automatización pueden desarrollar en paralelo contra un contrato estable, sin esperar a la implementación completa del backend.
- Reduce el riesgo de romper integraciones críticas (SAP, Salesforce, Control-M) ante cambios internos del backend.

### Negativas / Trade-offs

- Requiere disciplina adicional de diseño previo, lo que puede percibirse como una desaceleración inicial frente a un desarrollo puramente iterativo "código primero".
- El desacoplamiento deliberado entre `schemas/` (contrato) y `models/` (persistencia) implica mantener y sincronizar manualmente dos representaciones de una misma entidad en ciertos casos.
- Exige gobernanza de versionado de API explícita (definida en `API-STANDARD.md`) para no acumular versiones obsoletas sin plan de retiro.
