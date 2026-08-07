# ADR-011 — Arquitectura de proxies de confianza para la resolución de la IP del cliente

## Estado

**Aceptado** — Sprint 3.0 (v0.10.0-alpha).

Completa y cierra la deuda que [ADR-010](ADR-010-security-headers-and-forwarded-trust.md) §4 dejó
declarada explícitamente: *«La alternativa completa —una lista de proxies de confianza
(`trusted_proxies`), que es como lo resuelven los frameworks maduros— es la solución correcta a
medio plazo»*.

## Contexto

Todo lo que TEAF agrupa «por cliente» depende de una sola función:
[`resolve_client_ip`](../../../teaf/_internal/api/middleware/context.py). De ella salen la clave de
rate limiting por IP, la de cuotas por IP y el campo `clientIp` de cada registro de auditoría. Si
esa función devuelve un valor que el cliente controla, los tres controles se vuelven decorativos.

Hasta v0.9.2-alpha la decisión era binaria, gobernada por `trust_forwarded_headers`:

| Valor | Comportamiento |
|---|---|
| `True` (por defecto) | Se cree lo que diga `X-Forwarded-For` / `X-Real-IP`, **venga de donde venga** |
| `False` | Se ignoran las cabeceras; manda siempre la IP de la conexión TCP |

Ninguno de los dos es correcto en el caso general, y el porqué es que **el framework no puede
saber si tiene un proxy delante**. El aviso de arranque que introdujo ADR-010 §4 mitiga el riesgo
pero no lo elimina: un aviso en el log no impide nada.

El agujero está demostrado de forma ejecutable desde Sprint 2.9.2 en
[`tests/unit/test_forwarded_headers_trust.py`](../../../tests/unit/test_forwarded_headers_trust.py):
con la configuración por defecto, un cliente que rota `X-Forwarded-For` estrena cubo de rate
limiting en cada petición y nunca alcanza el límite.

## Problema

Hay que distinguir dos preguntas que la configuración binaria confundía en una:

1. **¿Existe un proxy delante que reescriba las cabeceras de reenvío?**
2. **¿Es *esta* petición concreta la que viene de ese proxy?**

`trust_forwarded_headers` solo podía responder la primera, y la respondía para todas las
peticiones por igual. Pero la propiedad que hace segura una cabecera de reenvío no es que exista
un proxy: es que **la conexión que la trae venga de él**. Un atacante que llegue directamente al
puerto de la aplicación —red interna, un balanceador mal configurado, un `port-forward` olvidado—
envía exactamente los mismos bytes que el proxy legítimo, y sin la pregunta 2 no hay forma de
distinguirlos.

### Modelo de amenaza

| Actor | Capacidad | Objetivo |
|---|---|---|
| Cliente anónimo de Internet | Fija cualquier cabecera HTTP de su petición | Esquivar rate limiting/cuotas por IP; ensuciar la auditoría con IPs ajenas |
| Cliente que alcanza la app sin pasar por el proxy | Lo anterior, y además elige la IP de origen aparente | Lo anterior, y suplantar a una IP concreta en los registros |
| Proxy legítimo | Reescribe `X-Forwarded-For` añadiendo la IP real | (No es un atacante: es la fuente de verdad que hay que poder reconocer) |

Fuera del modelo: un atacante que controle el propio proxy, o que pueda originar tráfico desde
dentro del rango declarado como de confianza. Si eso ocurre, el problema es de red y ninguna
decisión de esta capa lo arregla.

### Por qué la cadena se recorre de derecha a izquierda

`X-Forwarded-For` es una lista: `cliente, proxy1, proxy2`. Cada salto **añade por la derecha** la
IP de quien le habló. Por tanto:

- Las entradas de la **derecha** las escribieron los proxies: son tan fiables como el proxy que
  las puso.
- Las de la **izquierda** las pudo escribir el cliente original: **un atacante puede anteponer las
  que quiera**.

Tomar el elemento más a la izquierda —que es la lectura ingenua, y la que hacía TEAF— es
exactamente leer el trozo que el atacante controla. La lectura correcta es recorrer la cadena
**desde la derecha**, descartando entradas mientras pertenezcan a proxies de confianza, y quedarse
con la primera que no lo sea: esa es la primera dirección que un salto de confianza observó
directamente.

## Decisión

### 1. Una lista de redes de confianza, no un booleano

Se añade `trusted_proxies`: un conjunto de direcciones o redes CIDR (IPv4 e IPv6) de las que se
acepta información de reenvío.

```
IP de la conexión ∈ trusted_proxies  →  se procesa X-Forwarded-For (de derecha a izquierda)
IP de la conexión ∉ trusted_proxies  →  se ignoran las cabeceras; manda la conexión
```

La comprobación se hace contra la **IP de la conexión TCP**, que es el único dato de la petición
que el cliente no puede falsificar.

### 2. Se parsea al construir, no por petición

`TrustedProxies.parse()` convierte las cadenas de configuración en objetos
`IPv4Network`/`IPv6Network` una sola vez. En caliente solo queda una comparación de pertenencia
sobre una tupla, que para las listas realistas (unas pocas redes) es despreciable. El requisito de
que el camino de la petición no se encarezca es explícito en el sprint y se verifica con
benchmarks.

### 3. Falla cerrado ante configuración inválida

Una entrada que no sea una IP o un CIDR válido **aborta el arranque** en vez de ignorarse. Una
lista de confianza con una errata que se descarta en silencio es peor que no tener lista: se cree
estar protegido y no se está.

### 4. `trust_forwarded_headers` se conserva, no se elimina

Compatibilidad completa hacia atrás ([§12 del sprint](../../roadmap/ROADMAP.md)):

| `trusted_proxies` | `trust_forwarded_headers` | Comportamiento |
|---|---|---|
| Configurado | (no se consulta) | **Nuevo**: solo se confía en cabeceras que lleguen desde esas redes |
| Vacío | `True` (por defecto) | **Idéntico a v0.9.2-alpha**, incluido el aviso de arranque de ADR-010 |
| Vacío | `False` | Nunca se confía en cabeceras de reenvío |

Configurar `trusted_proxies` **silencia el aviso de arranque**, porque el aviso deja de describir
un riesgo real: ya no se confía en cualquiera.

### 5. Sigue sin haber un valor por defecto seguro, y es deliberado

La lista vacía mantiene el comportamiento de v0.9.2-alpha en lugar de pasar a «no confiar en
nada». El razonamiento de ADR-010 §4 sigue vigente y no ha cambiado: en el despliegue mayoritario
—detrás de un proxy— dejar de confiar convertiría cualquier límite por IP en un límite global
sobre la IP del balanceador, castigando a usuarios legítimos, y lo haría de forma difícil de
diagnosticar. Lo que este ADR aporta no es un valor por defecto distinto, sino **la posibilidad de
configurarlo correctamente**, que antes no existía.

## Alternativas consideradas

| Alternativa | Por qué se descarta |
|---|---|
| **Invertir el valor por defecto a `False`** | Rompe silenciosamente todo despliegue correcto tras un proxy. Mismo argumento de ADR-010 §4, que este ADR no revisa. |
| **Contar saltos (`trusted_hops = N`)** | Es lo que hacen algunos frameworks. Más simple de configurar, pero no verifica *quién* habla: si el número de saltos cambia (un balanceador extra, un despliegue distinto) la protección se desplaza sin avisar. Verificar la IP de origen es una propiedad, contar saltos es una suposición. |
| **Delegar en `uvicorn --proxy-headers --forwarded-allow-ips`** | Existe y funciona, pero deja la seguridad del rate limiting dependiendo de cómo se lance el proceso. TEAF no puede garantizar un flag de línea de comandos, y una aplicación desplegada en Azure App Service o en un contenedor ajeno puede no controlarlo. La protección debe estar en el framework. |
| **Leer solo `X-Real-IP`** | Es una cabecera de un solo valor, sin cadena — pero igual de falsificable. No resuelve nada; solo esconde el problema. |
| **Confiar en `Forwarded` (RFC 7239) en vez de `X-Forwarded-For`** | Es el estándar formal, pero el despliegue real (nginx, Azure Front Door, AWS ALB, Cloudflare) emite `X-Forwarded-For`. Adoptar solo el estándar formal dejaría desprotegido al 100 % de los despliegues reales. No se descarta añadirlo más adelante. |

## Consecuencias

### Positivas

- **El spoofing de rate limiting deja de ser posible** cuando se configura la lista: es la primera
  vez que TEAF puede desplegarse expuesto sin que un cliente elija su propio cubo.
- **Un solo punto de cambio.** `resolve_client_ip` es el único consumidor de cabeceras de reenvío,
  así que rate limiting, cuotas y auditoría heredan la corrección sin tocarse. La superficie de
  revisión de seguridad es una función.
- **Sin dependencias nuevas**: `ipaddress` es librería estándar, e IPv6 sale gratis.
- **Cierra la deuda de ADR-010** dejando el aviso de arranque como lo que debía ser: una señal
  temporal, no un sustituto de la solución.

### Negativas

- **Hay que saber qué poner en la lista.** El operador debe conocer el rango de su proxy o
  balanceador. Documentado en [SECURITY-CONFIGURATION.md](../../security/SECURITY-CONFIGURATION.md),
  pero es trabajo real de despliegue que antes no existía.
- **Una lista mal puesta rompe el arranque.** Es el comportamiento buscado (punto 3), pero
  convierte una errata de configuración en una caída de despliegue.
- **Un campo más en `Settings`** (`api_trusted_proxies`). Aditivo, no rompe, pero amplía la
  superficie de configuración pública.
- **Sigue siendo inseguro si no se configura.** Quien no lea la documentación ni los avisos de
  arranque queda igual que en v0.9.2-alpha. Este ADR da la herramienta; no obliga a usarla.

### Trade-off aceptado

Se elige **poder configurarlo correctamente** por encima de **ser seguro por defecto**. Es el
mismo trade-off de ADR-010 §4 y se acepta por la misma razón, pero con una diferencia que importa:
ahora existe una configuración que cierra el agujero del todo, y el aviso de arranque apunta a
ella. Antes el aviso solo nombraba un riesgo sin ofrecer salida.

## Referencias

- [ADR-010](ADR-010-security-headers-and-forwarded-trust.md) §4 — la deuda que este ADR cierra
- [ADR-009](ADR-009-enterprise-api-protection.md) — `ApiGateway` y los ocho middlewares
- [SECURITY-CONFIGURATION.md](../../security/SECURITY-CONFIGURATION.md) — cómo configurarlo
- [`tests/unit/test_forwarded_headers_trust.py`](../../../tests/unit/test_forwarded_headers_trust.py)
  — el agujero y su cierre, de forma ejecutable
- RFC 7239 (`Forwarded`) · [OWASP — IP spoofing vía cabeceras de reenvío](https://owasp.org/www-community/attacks/IP_Address_Spoofing)
