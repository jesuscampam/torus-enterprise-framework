# webhooks/

Framework de eventos entrantes y salientes hacia sistemas externos (SAP, Salesforce, Control-M y futuras integraciones).

## Responsabilidad

- Recepción de webhooks entrantes: verificación de firma/autenticidad del emisor, deduplicación, y traducción del payload externo a un caso de uso de `services/`.
- Emisión de webhooks salientes: notificación de eventos internos a sistemas externos suscritos, con reintentos y registro de auditoría.
- Trazabilidad completa de cada evento procesado (correlación con `monitoring/` y `LOGGING-STANDARD.md`).

## Qué NO debe contener

- Lógica de negocio específica de una integración concreta (eso se implementa como un módulo de aplicación que usa este framework, no dentro de él).
- Credenciales o secretos de integración hardcodeados (se resuelven vía `config/`).

## Estado actual

Solo estructura; la implementación concreta llega en la Versión 4 del [roadmap](../../docs/roadmap/ROADMAP.md).
