# quota-management/

Las cuatro magnitudes de cuota de `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)): peticiones por período, ancho de banda, tamaño de payload y concurrencia.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- **Cuotas vs. rate limiting**: las cuotas gobiernan el consumo *contratado* de un cliente (al mes, al día) y el rate limiting protege la *disponibilidad* del servicio (por segundo). Comparten dimensiones (`ProtectionScope`) pero no propósito — ver [QUOTAS.md](../../docs/api/QUOTAS.md).
- `REQUESTS` y `BANDWIDTH` **acumulan** sobre la ventana del período; al cambiar de período la clave del almacén cambia y el consumo arranca de cero sin ningún proceso de reinicio.
- `PAYLOAD` **no acumula**: limita el tamaño de *una* petición. Muchas pequeñas nunca la agotan; una grande la rompe de inmediato.
- `CONCURRENT` no tiene ventana temporal: sube con `consume()` y baja con `release()`. `QuotaMiddleware` llama a `release()` en un `finally`, así que una excepción en el endpoint no deja el contador alto para siempre.
- Una petición rechazada **no sigue contando**: si el consumo desbordado se quedara sumado, el contador no bajaría nunca aunque el cliente dejara de insistir.
