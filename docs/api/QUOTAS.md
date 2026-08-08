# Quotas — TEAF

Gobierno del consumo contratado de una API (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

## 1. Quotas vs. rate limiting

Es la pregunta que más se repite, y la razón de que sean dos subsistemas y no uno:

| | Rate limiting | Quotas |
|---|---|---|
| **Qué protege** | La disponibilidad del servicio | El consumo contratado del cliente |
| **Pregunta que responde** | ¿Cuántas peticiones por segundo aguanta esto? | ¿Cuánto le corresponde a este cliente este mes? |
| **Orden de magnitud** | Segundos | Minutos a meses |
| **Origen del límite** | Capacidad técnica | Contrato comercial |
| **Al agotarse** | El cliente reintenta en segundos | El cliente amplía su plan |

Comparten las dimensiones de agrupación (`ProtectionScope`, el mismo enum) pero no el propósito, ni el algoritmo, ni el orden de magnitud. Unificarlos habría producido una abstracción con dos modos y ninguna claridad.

## 2. Las cuatro magnitudes

`QuotaKind` define qué se mide. Las cuatro se evalúan de forma **deliberadamente distinta**:

| Magnitud | Acumula | Cómo se evalúa |
|---|---|---|
| `REQUESTS` | Sí | Suma 1 por petición sobre la ventana del período. |
| `BANDWIDTH` | Sí | Suma `request_bytes` sobre la ventana del período. |
| `PAYLOAD` | No | Compara el tamaño de *una* petición contra el límite. No toca el almacén. |
| `CONCURRENT` | No | Sube al entrar, baja al salir. Sin ventana temporal. |

```python
from teaf.api import ProtectionScope, QuotaKind, QuotaManager, QuotaPeriod, QuotaRule

gestor = QuotaManager([
    QuotaRule(name="peticiones-mes", kind=QuotaKind.REQUESTS, limit=1_000_000,
              period=QuotaPeriod.MONTH, scope=ProtectionScope.TENANT),
    QuotaRule(name="ancho-banda-dia", kind=QuotaKind.BANDWIDTH, limit=5_000_000_000,
              period=QuotaPeriod.DAY, scope=ProtectionScope.TENANT),
    QuotaRule(name="payload-max", kind=QuotaKind.PAYLOAD, limit=10_000_000,
              scope=ProtectionScope.TENANT),
    QuotaRule(name="simultaneas", kind=QuotaKind.CONCURRENT, limit=50,
              scope=ProtectionScope.TENANT),
])
```

## 3. Los cuatro períodos

`QuotaPeriod` cubre `MINUTE`, `HOUR`, `DAY` y `MONTH`.

### Por qué el mes son 30 días

El mes se aproxima a 30 días (2.592.000 s). Una cuota mensual es un **límite comercial**, no un calendario contable: usar 30 días mantiene la aritmética de ventanas idéntica a la del resto de períodos (`now // duración`), lo que a su vez permite que la clave de almacén cambie sola al cambiar de período. Alinear la ventana a meses naturales exigiría aritmética de calendario en la ruta caliente de cada petición, a cambio de una precisión que un límite comercial no necesita. Si un contrato exige meses naturales exactos, la vía es un `QuotaStore` propio, no cambiar la aritmética del framework.

### Reinicio sin proceso de reinicio

Para las cuotas acumulativas la clave de almacén incorpora el **índice de ventana**:

```
peticiones-mes:tenant:acme:672
```

Al cambiar de período cambia el índice, cambia la clave y el consumo arranca de cero. No hace falta ningún job de reinicio ni ninguna tarea programada.

## 4. Concurrencia: el `release()` no es opcional

Las cuotas de concurrencia suben con `consume()` y solo bajan con `release()`. Sin ese `release()`, una excepción en el endpoint dejaría el contador alto para siempre y la cuota se agotaría sola tras suficientes errores.

`QuotaMiddleware` lo garantiza con un `finally`. Quien use `QuotaManager` fuera de HTTP debe hacer lo mismo:

```python
decision = await gestor.consume(contexto)
if decision is not None:
    ...  # rechazar
try:
    ...  # trabajo
finally:
    await gestor.release(contexto)
```

## 5. Una petición rechazada no sigue contando

Cuando un consumo desborda una cuota acumulativa, el gestor **deshace** ese incremento. Si no lo hiciera, el contador no bajaría nunca aunque el cliente dejara de insistir: cada reintento fallido lo empujaría más arriba y el cliente vería un consumo creciente sin haber recibido ni una respuesta útil.

## 6. Cabeceras de respuesta

| Cabecera | Qué dice |
|---|---|
| `X-Quota-Limit` | Límite de la cuota agotada. |
| `X-Quota-Remaining` | Consumo aún disponible. |
| `X-Quota-Period` | Período de la cuota (`minute`/`hour`/`day`/`month`). |
| `Retry-After` | Segundos hasta que se abra la ventana siguiente (solo en cuotas acumulativas). |

El rechazo es un `429` con cuerpo RFC 7807 y `type` igual a `https://teaf.torus/errors/quota-exceeded`. Una cuota de `PAYLOAD` no lleva `Retry-After`: esperar no arregla que la petición sea demasiado grande.

## 7. Consultar el consumo sin consumir

```python
for uso in await gestor.usage(contexto):
    print(f"{uso.rule}: {uso.consumed:.0f}/{uso.limit} ({uso.period.value}), quedan {uso.remaining:.0f}")
```

Es lo que alimenta un endpoint de "mi consumo" o un panel de cliente. `reset()` limpia el consumo acumulado de todas las cuotas aplicables — útil en pruebas y en soporte.

## 8. Configuración por entorno

Cada límite a `0` significa "sin cuota de ese tipo", así que se activa solo lo que se declara:

```bash
API_QUOTAS_ENABLED=true
API_QUOTA_SCOPE=tenant
API_QUOTA_REQUESTS_PER_MINUTE=0
API_QUOTA_REQUESTS_PER_HOUR=0
API_QUOTA_REQUESTS_PER_DAY=100000
API_QUOTA_REQUESTS_PER_MONTH=1000000
API_QUOTA_BANDWIDTH_BYTES_PER_DAY=5000000000
API_QUOTA_MAX_PAYLOAD_BYTES=10000000
API_QUOTA_MAX_CONCURRENT_REQUESTS=50
```

Para cuotas distintas por plan comercial (free / pro / enterprise), la vía es pasarlas directamente:

```python
ApiProtectionModule(quota_rules=[...])
```

## 9. Persistencia

`QuotaManager` usa `InMemoryQuotaStore` por defecto. Con varias instancias, cada una lleva su propia cuenta — para cuotas contratadas eso suele ser inaceptable (el cliente consumiría `limit × réplicas`), así que un despliegue multi-instancia necesita un almacén compartido.

`RedisQuotaStore` (`teaf.api`) lo deja preparado: `INCRBYFLOAT` es atómico por definición, que es exactamente lo que el contrato de `consume()` exige para evitar la carrera "leer, sumar, escribir" entre instancias, y `EXPIRE NX` fija el vencimiento de la ventana solo la primera vez, para no prolongarla con cada consumo. Sin conexión real hasta que un ADR apruebe `redis-py` — ver [API-PROTECTION.md](API-PROTECTION.md), §10.

Un almacén sobre PostgreSQL (vía el `DatabaseModule` ya existente) es igual de válido: `QuotaStore` son cuatro métodos.

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa.
- [RATE-LIMITING.md](RATE-LIMITING.md) — el otro lado de la moneda.
- [`examples/quota-management/`](../../examples/quota-management/) — ejemplo ejecutable.
