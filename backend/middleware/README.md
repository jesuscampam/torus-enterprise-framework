# middleware/

Componentes transversales que interceptan toda petición HTTP antes de llegar a `api/` (o después de que esta responde).

## Responsabilidad

- Asignar/propagar el `correlation-id` de cada petición (ver [LOGGING-STANDARD.md](../../docs/standards/LOGGING-STANDARD.md)).
- Verificar la autenticación (JWT) delegando en `security/`.
- Registrar logs estructurados de entrada/salida de cada petición (método, ruta, status, duración).
- Aplicar límites de tasa (rate limiting).
- Manejo centralizado de errores no capturados, traduciéndolos al formato RFC 7807 definido en [API-STANDARD.md](../../docs/standards/API-STANDARD.md).

## Qué NO debe contener

- Lógica de negocio de un caso de uso específico.

## Principio rector

Un middleware resuelve una preocupación transversal a **toda** la API; si una lógica solo aplica a un endpoint concreto, no pertenece aquí sino a `api/` o `services/`.
