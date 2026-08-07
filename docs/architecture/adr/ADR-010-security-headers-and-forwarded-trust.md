# ADR-010 — Reparto de responsabilidad de seguridad de borde entre TEAF y el proxy

## Estado

**Aceptado** — Sprint 2.9.2 (v0.9.2-alpha).

## Contexto

La revisión de seguridad de Sprint 2.9.1 ([SECURITY-REVIEW.md](../../SECURITY-REVIEW.md)) dejó dos
hallazgos sin resolver, ambos sobre la misma pregunta de fondo: **¿qué parte de la seguridad de
borde es responsabilidad del framework y qué parte es del proxy que tenga delante?**

- **H-1 (alta)**: [SECURITY-STANDARD.md §7](../../standards/SECURITY-STANDARD.md) exige cuatro
  cabeceras de seguridad HTTP, y `Settings` declaraba tres campos para gobernarlas
  (`security_headers_enabled`, `security_hsts_max_age_seconds`, `security_frame_options`), pero
  **no existía nada que las emitiera**. Un `security_headers_enabled: bool = True` que no activa
  nada no es una omisión neutra: comunica activamente una protección inexistente, y es peor que no
  ofrecer el campo.
- **H-2 (media)**: `trust_forwarded_headers` vale `True` por defecto, de modo que la IP del cliente
  se toma de `X-Forwarded-For`/`X-Real-IP` — cabeceras que cualquier cliente puede falsificar.

La arquitectura de despliegue objetivo de TEAF siempre lleva un intermediario delante:

```
Internet
   │
   ▼
WAF / Proxy inverso / API Gateway
   │   TLS · cabeceras de reenvío · seguridad de borde
   ▼
Aplicación TEAF
   │
   ├── Autenticación
   ├── Autorización
   ├── Rate limiting
   ├── Cabeceras de seguridad
   └── Seguridad de aplicación
```

## Problema

Sin una frontera declarada, cada control de seguridad cae en una de dos trampas:

1. **Nadie lo implementa** porque «lo hace el proxy» — que es exactamente cómo H-1 llegó a
   producirse: el estándar lo exigía, la configuración lo prometía, y se dio por hecho que otro
   se ocuparía.
2. **Se implementa dos veces** y las dos configuraciones divergen, con el resultado de que nadie
   sabe cuál manda.

Hace falta decidir, control por control, quién es responsable — y que la implementación coincida
con lo que el estándar promete.

## Decisión

### 1. TEAF no sustituye al WAF ni al API Gateway

TEAF **no** implementa terminación TLS, filtrado de tráfico, protección DDoS, reglas OWASP CRS ni
reescritura de cabeceras de reenvío. Eso pertenece al borde. Intentar duplicarlo produciría una
versión peor de algo que el despliegue ya tiene.

### 2. TEAF sí es responsable de las cabeceras de seguridad de sus propias respuestas

Con un criterio simple: **una cabecera que describe cómo debe tratarse la respuesta que TEAF
genera es responsabilidad de TEAF**. El proxy no sabe si un endpoint devuelve JSON o HTML, ni qué
CSP le corresponde; la aplicación sí.

Se implementa `SecurityHeadersMiddleware`
([`teaf/_internal/middleware/security_headers.py`](../../../teaf/_internal/middleware/security_headers.py)),
instalado siempre por `create_app` y gobernado por los campos de `Settings` que ya existían. Emite
las cuatro cabeceras del §7:

| Cabecera | Valor por defecto | Cuándo |
|---|---|---|
| `X-Content-Type-Options` | `nosniff` | Siempre |
| `X-Frame-Options` | `DENY` (configurable; vacío la omite) | Siempre |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | Salvo en `/docs` y `/redoc` |
| `Strict-Transport-Security` | `max-age=31536000` | **Solo sobre HTTPS** |

Un proxy que ya añada estas cabeceras no entra en conflicto: el middleware **nunca sobrescribe**
una cabecera ya presente.

### 3. Tres decisiones de detalle, y su porqué

**HSTS solo sobre HTTPS.** RFC 6797 §7.2 lo exige literalmente. Emitirla siempre no solo
incumpliría la norma —los navegadores la ignoran sobre HTTP— sino que en desarrollo puede fijar
`localhost` en HTTPS en el navegador del desarrollador durante un año. El esquema se lee del
*scope* ASGI, que es lo que uvicorn reescribe con `--proxy-headers`; no se lee `X-Forwarded-Proto`
directamente, para no crear una segunda vía de confianza distinta de la del punto 4.

**La CSP no se aplica a la documentación.** Swagger UI y ReDoc cargan sus propios recursos, y
`default-src 'none'` los rompería. Un desarrollador que se encuentre `/docs` en blanco desactivará
el middleware entero — el peor resultado posible. Excepción acotada a rutas de documentación, que
además están deshabilitadas por defecto en producción. Las otras tres cabeceras sí se aplican ahí.

**La CSP por defecto es la de una API JSON, no la de un frontend.** El §7 pide una CSP «apropiada
para el frontend servido»; TEAF no sirve frontend, sirve JSON. `default-src 'none'` es la política
correcta para una respuesta que no debe cargar nada. Una aplicación que sirva HTML propio debe
sustituirla — está documentado en el propio campo de configuración.

**Middleware ASGI puro, no `BaseHTTPMiddleware`.** Basta con interceptar `http.response.start`.
`BaseHTTPMiddleware` obligaría a materializar el cuerpo de toda respuesta y rompería el streaming,
a cambio de nada. Se instala como el más externo de los tres del framework, para que sus cabeceras
alcancen también a las respuestas de error, que se generan en capas más internas.

### 4. `trust_forwarded_headers` mantiene su valor por defecto — pero deja de ser silencioso

Se consideró invertirlo a `False` («seguro por defecto») y **se descartó**, por una razón concreta:
en el despliegue mayoritario y recomendado —detrás de un proxy que reescribe la cabecera— confiar
en ella no solo es correcto, es **necesario**. Sin ella, todo el tráfico compartiría la IP del
balanceador y cualquier límite por IP se convertiría en un límite global que castigaría a usuarios
legítimos. Invertir el valor por defecto rompería silenciosamente a quien hoy está bien desplegado,
y lo haría de una forma difícil de diagnosticar.

El framework no puede distinguir los dos despliegues. Lo que sí puede es **no aceptar el riesgo en
silencio**: `ApiGateway.install()` emite un aviso al arrancar, una sola vez, y solo cuando hay
algún middleware que realmente usa la IP del cliente (`rate_limit`, `quota`, `audit`). El aviso
nombra el riesgo y la acción concreta para desactivarlo.

La alternativa completa —una lista de proxies de confianza (`trusted_proxies`), que es como lo
resuelven los frameworks maduros— es la solución correcta a medio plazo, pero es funcionalidad
nueva y queda documentada como backlog para Sprint 3.0.

## Consecuencias

### Positivas

- El contrato de seguridad de TEAF **coincide con su implementación**: `security_headers_enabled`
  hace lo que su nombre dice, verificado por 31 pruebas que comprueban valores reales.
- La frontera con el proxy queda declarada, así que un control ya no puede caer en el hueco entre
  ambos «porque lo hace el otro».
- Un despliegue que confía en cabeceras de reenvío sin proxy delante deja rastro en el log en vez
  de pasar inadvertido.
- Las pruebas anti-spoofing documentan de forma ejecutable la diferencia entre los dos
  despliegues, incluida la demostración de que sin confianza un atacante **no** puede repartirse
  entre cubetas de rate limiting.

### Negativas

- **Una excepción por ruta.** La CSP no se aplica a `/docs` y `/redoc`. Es una excepción real y
  hay que conocerla; se ha preferido a romper Swagger UI, pero no es gratis.
- **`trust_forwarded_headers` sigue siendo inseguro por defecto** para quien despliegue sin proxy.
  Un aviso en el log es más débil que un valor por defecto seguro, y quien no lea los logs de
  arranque seguirá expuesto. Es una decisión consciente de no romper compatibilidad en un Sprint
  de cierre, no una solución completa.
- **Un campo nuevo en `Settings`** (`security_content_security_policy`). Es aditivo y no rompe
  nada, pero amplía la superficie de configuración pública.
- **La CSP por defecto romperá cualquier aplicación TEAF que sirva HTML propio** hasta que la
  sustituya. Está documentado, pero es un cambio de comportamiento observable respecto a
  v0.9.1-alpha, donde no se emitía CSP alguna.

### Trade-off aceptado

Se elige **coherencia entre estándar e implementación** por encima de mínima intervención: era
posible «resolver» H-1 borrando la promesa del §7 y los tres campos de `Settings`. Se ha
descartado porque el estándar tiene razón —esas cabeceras deben existir— y porque rebajar el
estándar para que coincida con la implementación es exactamente al revés de como debe cerrarse un
hallazgo de seguridad.

## Referencias

- [SECURITY-STANDARD.md §7](../../standards/SECURITY-STANDARD.md)
- [SECURITY-REVIEW.md](../../SECURITY-REVIEW.md) — H-1 y H-2
- [ADR-007](ADR-007-enterprise-security.md) — plataforma de seguridad
- [ADR-009](ADR-009-enterprise-api-protection.md) — protección de APIs y `ApiGateway`
- RFC 6797 §7.2 (HSTS sobre transporte no seguro), RFC 7515 §4.1.11
