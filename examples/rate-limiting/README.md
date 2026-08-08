# rate-limiting/

Los cuatro algoritmos de rate limiting de `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)) y su aplicación sobre una API real.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- Los cuatro algoritmos aceptan exactamente 3 peticiones y rechazan el resto, pero **por motivos distintos**: la ventana fija cuenta, la deslizante registra marcas de tiempo, el cubo de tokens gasta permisos y el cubo con fuga acumula trabajo pendiente. La diferencia se nota al avanzar el tiempo, no en una ráfaga instantánea — ver [RATE-LIMITING.md](../../docs/api/RATE-LIMITING.md).
- `ProtectionScope.TENANT` hace que `acme` y `globex` tengan presupuestos independientes: la misma regla, distinta clave de agrupación.
- `RateLimiter.acquire()` devuelve `None` cuando la petición pasa y una `RateLimitDecision` cuando se rechaza — el caso normal no obliga a interpretar nada.
- Sobre HTTP, `X-RateLimit-Remaining` viaja **también** en las respuestas correctas: es lo que permite a un cliente autorregularse antes de chocar contra el límite.
- El rechazo es un `429` con cuerpo RFC 7807 y `Retry-After`, igual que cualquier otro error del framework.
