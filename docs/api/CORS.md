# CORS — TEAF

Política de intercambio de recursos entre orígenes (Sprint 2.9, [ADR-009](../architecture/adr/ADR-009-enterprise-api-protection.md)). Parte de la [plataforma de protección de APIs](API-PROTECTION.md).

## 1. Por qué una implementación propia

Starlette trae `CORSMiddleware`, y aun así TEAF implementa `CorsPolicy`. Dos razones concretas:

1. **CORS debe ser un objeto de dominio, no solo un middleware.** TEAF necesita declararlo en configuración, consultarlo desde el manifiesto del módulo (`gateway.describe()`) y evaluarlo en pruebas sin levantar un servidor. Un middleware opaco no permite nada de eso.
2. **Comodines de subdominio.** `https://*.torus.com` es el caso real de toda organización con varios portales, y `CORSMiddleware` no lo soporta.

El middleware que aplica la política es una capa fina encima, igual que en el resto de la plataforma.

## 2. Configurar la política

```python
from teaf.api import CorsPolicy

politica = CorsPolicy(
    allow_origins=("https://app.torus.com",),
    allow_origin_patterns=("https://*.torus.com",),
    allow_methods=("GET", "POST", "PUT", "DELETE", "OPTIONS"),
    allow_headers=("X-Tenant", "Authorization"),
    expose_headers=("X-Total-Count", "X-RateLimit-Remaining"),
    allow_credentials=True,
    max_age_seconds=600,
)
```

**Los valores por defecto no permiten ningún origen.** Habilitar la plataforma de protección nunca debe abrir CORS por accidente: quien lo necesita lo declara. Sin orígenes declarados, el middleware ni siquiera se instala.

## 3. Comodines de subdominio

`https://*.torus.com` acepta exactamente los subdominios de `torus.com` bajo el mismo esquema:

| Origen | ¿Permitido? | Por qué |
|---|---|---|
| `https://app.torus.com` | Sí | Subdominio. |
| `https://portal.torus.com` | Sí | Subdominio. |
| `https://torus.com` | **No** | El dominio raíz no es un subdominio suyo. |
| `https://evil-torus.com` | **No** | Otro dominio que solo *parece* parecido. |
| `http://app.torus.com` | **No** | Esquema distinto. |
| `https://app.torus.com.evil.net` | **No** | El sufijo no coincide. |

Los dos últimos casos son precisamente los que hacen peligrosa una comparación ingenua por subcadena.

## 4. Credenciales: la regla no negociable

**Con `allow_credentials=True` nunca se responde `Access-Control-Allow-Origin: *`** — se responde con el origen concreto solicitado.

No es una preferencia de TEAF: es el propio estándar CORS. Un navegador rechaza esa combinación, y "arreglarla" devolviendo el comodín convertiría cualquier web del mundo en cliente autenticado de la API, con las cookies de sesión del usuario. `CorsPolicy` aplica la regla sola: aunque se declare `allow_origins=("*",)` junto con credenciales, la respuesta lleva el origen concreto.

## 5. `Vary: Origin`, siempre

Toda respuesta con cabeceras CORS incluye `Vary: Origin`. Sin él, una caché intermedia podría servir la respuesta preparada para un origen permitido a otro que no lo está — lo que anula la política entera sin que nadie se dé cuenta.

## 6. Comprobación previa (preflight)

Un `OPTIONS` con `Access-Control-Request-Method` es una comprobación previa. La política responde:

- **`204 No Content`** con las cabeceras CORS si el origen, el método y las cabeceras solicitadas están permitidos.
- **`403 Forbidden`** en texto plano y **sin cabeceras CORS** si no. Es exactamente lo que el navegador interpreta como "origen no autorizado".

El `403` no usa RFC 7807 a propósito: el navegador nunca muestra ese cuerpo al código cliente, así que un `problem+json` solo confundiría a quien lo lea en una traza de red.

`Access-Control-Max-Age` (`max_age_seconds`) le dice al navegador cuánto puede cachear el resultado del preflight — sin él, cada petición cruzada se convierte en dos viajes.

## 7. Cabeceras simples

`Accept`, `Accept-Language`, `Content-Language` y `Content-Type` son cabeceras que un navegador siempre puede enviar sin declararlas. **No hace falta listarlas en `allow_headers`**: exigirlo rompería peticiones perfectamente válidas.

## 8. Por qué CORS es el middleware más externo

Sus cabeceras deben acompañar **también a los errores**. Si CORS quedara por dentro del limitador, un `429` saldría sin `Access-Control-Allow-Origin` y el navegador se lo ocultaría al cliente como un error de red genérico: el desarrollador vería "failed to fetch" en lugar de "te has pasado de peticiones". Es un fallo de diagnóstico muy caro y muy común, y el motivo de que `MIDDLEWARE_ORDER` empiece por CORS.

## 9. Peticiones sin `Origin`

Pasan intactas. CORS es un mecanismo del navegador; una petición desde el mismo origen, desde `curl` o desde un servicio no lleva `Origin`, y añadirle cabeceras a quien no las pidió solo añade ruido.

## 10. Configuración por entorno

```bash
API_CORS_ALLOW_ORIGINS="https://app.torus.com,https://portal.torus.com"
API_CORS_ALLOW_ORIGIN_PATTERNS="https://*.torus.com"
API_CORS_ALLOW_METHODS="GET,POST,PUT,PATCH,DELETE,OPTIONS"
API_CORS_ALLOW_HEADERS="X-Tenant,Authorization"
API_CORS_EXPOSE_HEADERS="X-Total-Count"
API_CORS_ALLOW_CREDENTIALS=true
API_CORS_MAX_AGE_SECONDS=600
```

## Ver también

- [API-PROTECTION.md](API-PROTECTION.md) — la plataforma completa y el orden de la cadena.
- [SECURITY-STANDARD.md](../standards/SECURITY-STANDARD.md) — el resto de cabeceras de seguridad HTTP.
- [`examples/cors-policy/`](../../examples/cors-policy/) — ejemplo ejecutable.
