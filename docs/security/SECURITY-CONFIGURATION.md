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

### Limitación conocida

`trust_forwarded_headers` es binario: se confía en la cabecera o no. No existe todavía una lista
de proxies de confianza (`trusted_proxies`), que es la solución completa y la que permitiría
confiar solo cuando la conexión venga de un proxy conocido. Está documentado como backlog para
Sprint 3.0 en [BACKLOG.md](../roadmap/BACKLOG.md).
