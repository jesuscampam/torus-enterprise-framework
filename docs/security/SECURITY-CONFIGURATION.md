# Configuración de seguridad — riesgo y despliegue recomendado

Los dos ajustes de seguridad cuyo valor por defecto **depende del despliegue** y que, mal
entendidos, dejan una aplicación expuesta sin que nada falle de forma visible. El resto de la
configuración de seguridad se documenta con cada subsistema
([SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md), [API-PROTECTION.md](../api/API-PROTECTION.md));
aquí están solo los que exigen una decisión consciente.

Decisión arquitectónica de fondo: [ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md).

---

## `security_headers_enabled`

**Por defecto: `True`.** Variable de entorno: `SECURITY_HEADERS_ENABLED`.

Activa `SecurityHeadersMiddleware`, que emite las cuatro cabeceras de
[SECURITY-STANDARD.md §7](../standards/SECURITY-STANDARD.md) en toda respuesta, incluidas las de
error.

| Ajuste | Por defecto | Efecto |
|---|---|---|
| `security_headers_enabled` | `True` | A `False` no se emite ninguna cabecera. |
| `security_hsts_max_age_seconds` | `31536000` (1 año) | `max-age` de HSTS. `0` la omite. |
| `security_frame_options` | `DENY` | Valor de `X-Frame-Options`. Vacío la omite. |
| `security_content_security_policy` | `default-src 'none'; frame-ancestors 'none'` | Valor de la CSP. Vacío la omite. |

### Riesgo

Desactivarlo deja la aplicación sin protección de navegador frente a *clickjacking*
(`X-Frame-Options`/`frame-ancestors`), *MIME sniffing* (`X-Content-Type-Options`) y degradación a
HTTP (`Strict-Transport-Security`). **Solo tiene sentido desactivarlo si un proxy inverso las
añade** — y aun así no hace falta: el middleware nunca sobrescribe una cabecera ya presente, así
que dejarlo activo con un proxy que también las pone no genera conflicto.

### El caso que hay que mirar: aplicaciones que sirven HTML

La CSP por defecto es la correcta para una **API JSON**: prohíbe cargar cualquier recurso. Una
aplicación TEAF que sirva su propio frontend **debe** sustituirla, o el navegador bloqueará todos
sus scripts y hojas de estilo:

```bash
SECURITY_CONTENT_SECURITY_POLICY="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'"
```

Swagger UI y ReDoc (`/docs`, `/redoc`) están exentos de la CSP precisamente por esto, así que la
documentación interactiva funciona sin tocar nada.

### Despliegue recomendado

Dejarlo en `True`. Terminar TLS en el proxy y asegurarse de que la aplicación recibe el esquema
correcto (`uvicorn --proxy-headers`), o `Strict-Transport-Security` no se emitirá: RFC 6797 §7.2
prohíbe enviarla sobre transporte no seguro.

---

## `api_trust_forwarded_headers`

**Por defecto: `True`.** Variable de entorno: `API_TRUST_FORWARDED_HEADERS`.

Determina de dónde sale la IP del cliente: de las cabeceras `X-Forwarded-For`/`X-Real-IP`
(`True`), o de la conexión TCP real (`False`).

Afecta a todo lo que se agrupa por IP: **rate limiting** (`ProtectionScope.IP`), **cuotas** por IP
y el campo de origen de la **auditoría**.

### Riesgo

`X-Forwarded-For` la controla el cliente. Con la aplicación expuesta **directamente a internet**,
basta con enviar una IP distinta en cada petición para que cada una caiga en una cubeta de rate
limiting diferente y el limitador deje de existir en la práctica. Está demostrado de forma
ejecutable en `tests/unit/test_forwarded_headers_trust.py`:

```
trust=True   →  5 peticiones con 5 IPs falsas  →  5 aceptadas (límite de 2 esquivado)
trust=False  →  5 peticiones con 5 IPs falsas  →  2 aceptadas, 3 rechazadas
```

### Por qué el valor por defecto sigue siendo `True`

Porque en el despliegue recomendado —detrás de un proxy que **reescribe** la cabecera— confiar en
ella no es opcional, es necesario: sin ella todo el tráfico compartiría la IP del balanceador y el
límite por IP se convertiría en un límite global que castigaría a usuarios legítimos. Invertir el
valor por defecto rompería silenciosamente a quien hoy está bien desplegado (ver
[ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)).

Lo que sí hace el framework es **no aceptarlo en silencio**: al instalar el gateway con la
confianza activa y algún middleware que use la IP del cliente, se registra un aviso al arrancar:

```
WARNING teaf.api.gateway: forwarded_headers_trusted
```

Si ese aviso aparece y **no** hay un proxy de confianza delante, hay un problema que resolver.

### Despliegue recomendado

| Despliegue | Valor | Motivo |
|---|---|---|
| Detrás de un proxy / balanceador / WAF que reescribe `X-Forwarded-For` | `True` | Es la única forma de ver la IP real del cliente. |
| Expuesto directamente a internet | **`False`** | La cabecera no es fiable; usar la conexión. |
| Desarrollo local | `False` | No hay proxy; evita confundirse con cabeceras propias. |

Requisito del proxy: debe **sobrescribir** `X-Forwarded-For`, no añadirse a la que traiga el
cliente. Un proxy que concatena permite al cliente inyectar la primera entrada de la cadena, que
es justo la que TEAF toma como IP de origen.

### Ya no es la única opción

Hasta v0.9.2-alpha `trust_forwarded_headers` era binario: se confiaba en la cabecera o no, y
ninguno de los dos valores es correcto en el caso general. Sprint 3.0 añade la solución completa
—`api_trusted_proxies`, la sección siguiente— y **la recomendación pasa a ser configurarla**.
`trust_forwarded_headers` se conserva sin cambios por compatibilidad, pero es la opción antigua.

## `api_trusted_proxies`

**Por defecto: `""` (vacío).** Variable de entorno: `API_TRUSTED_PROXIES`.

Lista separada por comas de direcciones IP o redes CIDR (IPv4 e IPv6) de las que se acepta
información de reenvío:

```bash
API_TRUSTED_PROXIES="10.0.0.0/8,192.168.1.10,2001:db8::/32"
```

La regla es una sola línea:

```
IP de la conexión ∈ trusted_proxies  →  se procesa X-Forwarded-For
IP de la conexión ∉ trusted_proxies  →  se ignoran las cabeceras; manda la conexión
```

La comprobación se hace contra la **IP de la conexión TCP**, que es el único dato de la petición
que el cliente no puede falsificar. Razonamiento completo y modelo de amenaza en
[ADR-011](../architecture/adr/ADR-011-trusted-proxy-architecture.md).

### Por qué esto cierra el agujero y `trust_forwarded_headers` no

Porque separa dos preguntas que el booleano confundía en una: *«¿hay un proxy delante?»* y
*«¿viene **esta** petición de él?»*. Un atacante que alcance la aplicación sin pasar por el proxy
—red interna, balanceador mal configurado, un `port-forward` olvidado— envía exactamente los
mismos bytes que el proxy legítimo. Solo comprobando la IP de origen se distinguen.

### La cadena se lee de derecha a izquierda

`X-Forwarded-For: cliente, proxy1, proxy2` — cada salto **añade por la derecha**. Las entradas de
la derecha las escribieron los proxies; las de la izquierda las pudo escribir el cliente. TEAF
recorre la cadena desde la derecha descartando entradas de proxies de confianza y se queda con la
primera que no lo sea: la primera dirección que un salto de confianza observó directamente.

Tomar el elemento más a la izquierda —la lectura ingenua— es leer justo el trozo que el atacante
controla.

### Falla cerrado

Una entrada que no sea una IP o un CIDR válido **aborta el arranque**. Una lista de confianza con
una errata que se descartara en silencio sería peor que no tener lista: se creería estar protegido
sin estarlo.

### Interacción con `trust_forwarded_headers`

| `api_trusted_proxies` | `api_trust_forwarded_headers` | Comportamiento |
|---|---|---|
| Configurado | (no se consulta) | Solo se confía en cabeceras que lleguen desde esas redes |
| Vacío | `True` (por defecto) | Idéntico a v0.9.2-alpha, incluido el aviso de arranque |
| Vacío | `False` | Nunca se confía en cabeceras de reenvío |

Configurar `api_trusted_proxies` **silencia el aviso `forwarded_headers_trusted`**, porque el
aviso deja de describir un riesgo real.

### Despliegue recomendado

| Despliegue | Configuración |
|---|---|
| Detrás de un proxy propio | `API_TRUSTED_PROXIES` con la red del proxy (`10.0.0.0/8`, la subred del ingress, ...) |
| Azure App Service / Front Door | La red del servicio de borde; consúltela en la documentación del proveedor y manténgala actualizada |
| Expuesto directamente a internet | Dejar vacío **y** `API_TRUST_FORWARDED_HEADERS=false` |
| Desarrollo local | Dejar vacío y `API_TRUST_FORWARDED_HEADERS=false` |

### Migración desde `trust_forwarded_headers`

No hay nada que romper: si no configura `api_trusted_proxies`, todo sigue exactamente igual. Para
adoptarlo, averigüe el rango del proxy que tiene delante y póngalo en `API_TRUSTED_PROXIES`; puede
dejar `api_trust_forwarded_headers` como esté, porque deja de consultarse.

### Limitación conocida

TEAF lee `X-Forwarded-For`/`X-Real-IP`, no `Forwarded` (RFC 7239). Es el estándar formal, pero el
despliegue real (nginx, Azure Front Door, AWS ALB, Cloudflare) emite `X-Forwarded-For`; adoptar
solo el estándar formal dejaría desprotegidos a todos los despliegues reales. Añadirlo queda en
[BACKLOG.md](../roadmap/BACKLOG.md).

## Longitud mínima del secreto JWT

**Sin valor por defecto**: `jwt_secret` vacío significa «sin configurar» y no valida nada. En
cuanto se configura, debe cumplir el mínimo que exige su algoritmo.

RFC 7518 §3.2 obliga a que una clave HMAC sea al menos del tamaño de la salida del hash. TEAF lo
comprueba **al arrancar**, nunca durante una petición:

| Algoritmo | Mínimo |
|---|---|
| HS256 | 32 bytes |
| HS384 | 48 bytes |
| HS512 | 64 bytes |
| RS\*/ES\*/PS\* | No aplica (clave PEM asimétrica) |

Se valida en dos sitios: `Settings` (la aplicación **no arranca** con un secreto débil) y
`JWTProvider.__init__` (cubre a quien lo construye a mano). El mensaje de error nombra el
algoritmo, la longitud recibida y la exigida, **sin revelar el secreto** — un error que lo filtrara
a los logs sería peor que el propio secreto débil.

Lo destapó el `InsecureKeyLengthWarning` de pyjwt 2.13. Un aviso que nadie lee no protege nada; un
arranque que falla, sí.

**Ruptura asumida**: una aplicación con un secreto por debajo del mínimo dejará de arrancar al
actualizar. Es intencionado — ese secreto era vulnerable a fuerza bruta y seguirlo aceptando en
silencio sería debilitar la política para mantener compatibilidad. Genere uno conforme:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Credenciales de Redis (`CACHE_REDIS_URL`)

La URL de Redis suele llevar credenciales embebidas, así que **nunca se escribe en el
repositorio**: va en una variable de entorno o en un gestor de secretos (Azure Key Vault), igual
que la de base de datos — ver [SECURITY-STANDARD.md §9](../standards/SECURITY-STANDARD.md).

| Configuración | Recomendación |
|---|---|
| Esquema | `rediss://` (TLS) en cualquier despliegue que no sea local |
| `CACHE_TLS_VERIFY` | `true`. Ponerlo a `false` solo tiene sentido contra un Redis de desarrollo con certificado autofirmado, y deja la conexión expuesta a un intermediario |
| `CACHE_KEY_PREFIX` | Distinto por aplicación si comparten instancia, para que no se pisen las claves |

La conexión la abre y la cierra `CacheModule` (`start()`/`dispose()`). No construya proveedores
sueltos por su cuenta: una conexión que nadie cierra sobrevive al apagado, y eso es un criterio de
bloqueo declarado del sprint. Ver [CACHE.md](../modules/cache/CACHE.md).
