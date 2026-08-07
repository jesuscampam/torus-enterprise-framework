# Revisión de seguridad y de dependencias — v0.9.1-alpha

> **Estado tras Sprint 3.0 (v0.10.0-alpha).** Este documento conserva la revisión original
> —lo que se encontró y por qué— y anota el desenlace de cada hallazgo. Resumen:
>
> | Hallazgo | Estado |
> |---|---|
> | H-1 · Cabeceras de seguridad sin implementar | ✅ **Resuelto** en 2.9.2 — `SecurityHeadersMiddleware` ([ADR-010](architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)) |
> | H-2 · `trust_forwarded_headers` inseguro por defecto | ✅ **Cerrado en 3.0** — `api_trusted_proxies` ([ADR-011](architecture/adr/ADR-011-trusted-proxy-architecture.md)). Estuvo mitigado, no cerrado, durante 2.9.2 |
> | H-3 · Comentario obsoleto sobre secretos | ✅ **Resuelto** en 2.9.2 |
> | H-4 · `pydantic` declarada sin uso directo | ℹ️ **Sin acción** — es deliberado |
> | Laguna · Sin auditoría de vulnerabilidades | ✅ **Cerrada** en 2.9.2 — `pip-audit` es puerta de calidad, y **encontró avisos reales** |
> | 7 CVE de `starlette` aceptadas por no poder actualizar | ✅ **Cerradas en 3.0** — `fastapi` 0.141.1 / `starlette` 1.4.1. `accepted-vulnerabilities.json` queda **vacío** |
>
> La fila de la auditoría de dependencias importa más que las otras: esta revisión concluyó
> «versiones recientes, ningún aviso conocido». Al ejecutar la herramienta por primera vez
> aparecieron 6 avisos en `pyjwt` y 7 en `starlette`. La conclusión original era conocimiento, no
> verificación, y era incorrecta. Detalle en la sección «Dependencias».
>
> La revisión propia de Sprint 3.0 está al final, en
> [«Revisión de Sprint 3.0»](#revisión-de-sprint-30-v0100-alpha).

Revisión completa realizada en Sprint 2.9.1 sobre la plataforma de seguridad (Sprint 2.7,
[ADR-007](architecture/adr/ADR-007-enterprise-security.md)), la de protección de APIs (Sprint 2.9,
[ADR-009](architecture/adr/ADR-009-enterprise-api-protection.md)) y el árbol de dependencias.

Alcance: JWT, API Keys, LDAP, Azure AD, RBAC, políticas, criptografía, secretos, cabeceras HTTP,
middlewares, configuración y dependencias. Fuente de verdad de los requisitos:
[SECURITY-STANDARD.md](standards/SECURITY-STANDARD.md).

> **Naturaleza de este documento.** Es una revisión, no una certificación. Sprint 2.9.1 tenía
> prohibido añadir funcionalidad, cambiar la API pública o alterar el comportamiento, así que
> **ningún hallazgo se ha corregido en código**: se reportan con su recomendación para que el
> usuario decida el alcance de un Sprint posterior. Es deliberado — corregir en silencio un
> hallazgo de seguridad dentro de un Sprint de endurecimiento sería exactamente el tipo de
> cambio no revisado que esta revisión existe para evitar ([CLAUDE.md](../CLAUDE.md) §8).

## Resumen

| Severidad | Nº | Hallazgos |
|---|---|---|
| Alta | 1 | H-1 Cabeceras de seguridad HTTP declaradas pero no implementadas. |
| Media | 1 | H-2 `trust_forwarded_headers` es `True` por defecto. |
| Baja | 2 | H-3 Comentario obsoleto sobre secretos. H-4 `pydantic` declarada sin uso directo. |

Verificado sin hallazgos: verificación de JWT, emisión y verificación de API Keys, hashing de
contraseñas, criptografía, exposición de secretos por HTTP, sincronía de manifiestos de
dependencias.

---

## H-1 · Alta — Cabeceras de seguridad HTTP declaradas pero no implementadas

**Qué.** [SECURITY-STANDARD.md §7](standards/SECURITY-STANDARD.md) exige que *«toda respuesta HTTP
incluye, como mínimo: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`,
`X-Frame-Options: DENY` (o CSP equivalente), `Content-Security-Policy`»*. `Settings` declara tres
campos que prometen justamente eso:

```python
security_headers_enabled: bool = True          # teaf/_internal/config/settings.py:108
security_hsts_max_age_seconds: int = 31_536_000
security_frame_options: str = "DENY"
```

**El problema.** Los tres campos **no los lee nadie**: no existe ningún `SecurityHeadersMiddleware`
en el árbol. Una aplicación TEAF no emite ninguna de esas cabeceras.

**Verificación** (`Application()` por defecto, `GET /health`):

```
content-length: 146
content-type: application/json
x-correlation-id: acfec827-99e9-4ea7-b617-f25c98d5817d
```

Ni `Strict-Transport-Security`, ni `X-Content-Type-Options`, ni `X-Frame-Options`, ni CSP.

**Por qué importa más que la ausencia sola.** Un valor por defecto de `True` en un campo llamado
`security_headers_enabled` no es neutro: comunica activamente que la protección está puesta. Un
operador que audite la configuración concluirá, razonablemente, que HSTS y `X-Frame-Options` están
activos. Es peor que no tener el campo.

**Recomendación.** Sprint propio que implemente `SecurityHeadersMiddleware`, lo instale desde
`create_app` gobernado por estos tres campos, y añada CSP a `Settings`. Es funcionalidad nueva y
necesita aprobación explícita. **Mitigación inmediata**, mientras tanto: terminar TLS y añadir las
cabeceras en el proxy inverso o el App Service, que es donde muchos despliegues ya las ponen.

---

## H-2 · Media — `trust_forwarded_headers` es `True` por defecto

**Qué.** `resolve_client_ip` (`teaf/_internal/api/middleware/context.py:37`) toma la IP del cliente
de `X-Forwarded-For`/`X-Real-IP` antes que de la conexión, y el parámetro que lo gobierna vale
`True` por defecto en los ocho middlewares de protección.

**El problema.** `X-Forwarded-For` lo falsifica cualquier cliente. Si la aplicación está expuesta
directamente a internet —sin un proxy que **reescriba** la cabecera— basta con enviar una IP
distinta en cada petición para saltarse por completo cualquier límite por IP: rate limiting
(`ProtectionScope.IP`), cuotas por IP y el reparto de auditoría.

**Atenuantes reales.** El riesgo está documentado en el docstring de la función y en
[docs/api/RATE-LIMITING.md](api/RATE-LIMITING.md); el parámetro existe y se puede poner a `False`;
y el despliegue objetivo de TEAF (Azure App Service, Render) siempre lleva proxy delante, que es
el caso en el que el valor por defecto es el correcto. Por eso es Media y no Alta.

**Recomendación.** Invertir el valor por defecto a `False` (seguro por defecto: quien esté detrás
de un proxy lo activa a conciencia), o sustituirlo por una lista de proxies de confianza, que es
la solución completa. Ambas cambian comportamiento y necesitan aprobación explícita.

---

## H-3 · Baja — Comentario obsoleto sobre secretos en `_configuration_summary`

`teaf/_internal/core/application.py:86` afirma: *«Ningún campo de `Settings` actual es un secreto
— si un Sprint futuro añade credenciales reales, deberá excluirlas explícitamente»*. Ese Sprint ya
llegó: Sprint 2.7 añadió `jwt_secret`, `api_key_hash_secret` y `azure_ad_client_secret`.

**No hay fuga**, y esa es la parte importante: el resumen se construye con una **lista blanca
explícita** de ocho campos no sensibles, así que los secretos nuevos quedaron fuera solos, sin que
nadie tuviera que acordarse. El diseño acertó donde el comentario falló. Solo la prosa está
desactualizada, y hoy induce a pensar que la protección depende de recordar excluir campos cuando
en realidad depende de recordar incluirlos.

**Verificación.** Con `JWT_SECRET`, `API_KEY_HASH_SECRET` y `AZURE_AD_CLIENT_SECRET` puestos a
valores centinela, se consultaron los 12 endpoints de sistema que responden 200 (`/`, `/health`,
`/live`, `/ready`, `/info`, `/runtime/info`, `/runtime/modules`, `/runtime/configuration`,
`/runtime/capabilities`, `/runtime/services`, `/runtime/events`, `/openapi.json`) buscando los
centinelas en el cuerpo: **ninguna coincidencia**.

**Recomendación.** Reescribir el comentario (cambio solo de documentación).

---

## H-4 · Baja — `pydantic` declarada sin importarse directamente

`pydantic==2.10.4` figura en `requirements.txt` y en `pyproject.toml`, pero **ningún módulo de
`teaf/` la importa**: el framework usa `pydantic_settings` (que depende de ella) y FastAPI (que
también). Lo mismo ocurre, por motivos distintos y legítimos, con `uvicorn` (servidor, se invoca,
no se importa) y con `aiosqlite`/`asyncpg` (drivers que SQLAlchemy carga desde la cadena de
conexión).

No es un defecto: fijar explícitamente una dependencia transitiva es una práctica deliberada de
cadena de suministro — impide que una actualización de FastAPI arrastre una versión de Pydantic no
probada. Se documenta para que nadie la «limpie» por parecer sobrante.

---

## Verificado sin hallazgos

### JWT (`teaf/_internal/security/tokens/jwt_provider.py`)

Correcto en los puntos donde suelen estar los fallos:

- **Algoritmo en lista blanca explícita** (`algorithms=[self._algorithm]`) en las dos rutas de
  decodificación. Cierra la confusión de algoritmos y el ataque `alg: none`, que es el fallo
  clásico de esta librería.
- **`aud` e `iss` verificados** siempre, no solo decodificados.
- **`leeway` configurable** para desviación de reloj, en vez de ampliar la expiración.
- **`verify_exp=False` aparece una sola vez**, en `revoke()`, y está razonado: un token ya expirado
  también debe poder revocarse. No participa en ninguna ruta de autenticación.

### API Keys (`teaf/_internal/security/tokens/api_key_provider.py`)

- Generadas con `secrets.token_urlsafe(32)` — 256 bits de entropía de fuente criptográfica.
- Se almacena **solo** el HMAC-SHA256 con pepper de servidor; la clave en claro existe una vez.
- La verificación es una **búsqueda por hash**, no una comparación de secretos: no hay superficie
  de ataque por temporización.
- Revocación y rotación invalidan de inmediato.

### Criptografía (`teaf/_internal/security/crypto/crypto_provider.py`)

`hmac.compare_digest` para verificar firmas (comparación en tiempo constante), `secrets.token_bytes`
para material nuevo, HMAC-SHA256 en todo. Contraseñas con Argon2id (por defecto) o bcrypt, con
coste reducido solo en `TestingSettings` y documentado.

### Dependencias

Los dos manifiestos están **exactamente sincronizados**: 18 paquetes de runtime, mismas versiones,
sin divergencias, sin duplicados, todas fijadas con `==`.

| Comprobación | Resultado |
|---|---|
| `requirements.txt` ↔ `pyproject.toml` | 18/18, sin divergencia de versión |
| Fijado exacto (`==`) | 18/18 |
| Sin usar | Ninguna (ver H-4 sobre las 4 indirectas) |
| Duplicados | Ninguno |
| Licencias | Todas MIT/BSD/Apache-2.0 — compatibles con uso empresarial |

**Limitación honesta de esta comprobación**: no hay `pip-audit` ni `safety` instalados en el
entorno, así que **no se ha contrastado el árbol contra una base de datos de vulnerabilidades**.
Las versiones fijadas son recientes y ninguna tiene un aviso conocido a la fecha de esta revisión,
pero eso es conocimiento, no una verificación. Es la mayor laguna de esta revisión y se recomienda
cerrarla añadiendo `pip-audit` a `requirements-dev.txt` y una puerta de calidad que lo ejecute.

### Actualización Sprint 2.9.2 — la laguna se cerró, y el párrafo anterior era falso

Se añadió `pip-audit` y una puerta de calidad
([`scripts/check_dependency_audit.py`](../scripts/check_dependency_audit.py)). La primera
ejecución encontró **13 avisos distintos en 2 paquetes**, no cero:

| Paquete | Avisos | Desenlace |
|---|---|---|
| `pyjwt` 2.10.1 | 6 | ✅ **Corregido** — actualizado a **2.13.0** |
| `starlette` 0.41.3 | 7 | ⏳ **Aceptados y documentados** — bloqueados por el pin de FastAPI |

**`pyjwt`** era dependencia directa de la que depende toda la plataforma de seguridad de TEAF, así
que se actualizó. Los avisos incluían un bypass de la lista blanca de algoritmos
(PYSEC-2026-176), confusión HMAC/JWK (PYSEC-2026-179) y falta de validación de `crit`
(PYSEC-2026-120). El análisis de explotabilidad mostró que el código de TEAF los mitigaba ya por
su cuenta —pasa `signing_key.key` en vez del `PyJWK`, fija `algorithms=["RS256"]` y no usa
`PyJWKClient`—, pero eso protege a TEAF, no necesariamente a las aplicaciones que lo usan.
Actualizar era lo correcto. La suite completa pasa sin cambios de código.

Efecto lateral útil: 2.13.0 introduce `InsecureKeyLengthWarning`, que es la mitigación que el
propio informe de PYSEC-2025-183 pedía. Aparece en las pruebas porque sus fixtures usan secretos
de 11 bytes. **TEAF no impone longitud mínima al secreto JWT** — hallazgo nuevo, de severidad
baja, anotado en el backlog: imponerla cambiaría configuraciones que hoy funcionan.

**`starlette`** es transitiva: `fastapi 0.115.6` fija `starlette<0.42.0`, así que ninguna
corrección es alcanzable sin actualizar FastAPI, lo que es un cambio mayor y quedó fuera del
alcance de un Sprint de cierre. Los 7 avisos se aceptan **explícitamente**, con severidad,
versión objetivo y análisis de aplicabilidad, en
[`docs/security/accepted-vulnerabilities.json`](security/accepted-vulnerabilities.json). Ninguno
alcanza código de TEAF: cinco dependen de funcionalidad que el framework no usa (`StaticFiles`,
`FileResponse`, `HTTPEndpoint`, parseo de formularios y multipart) y uno es exclusivo de Windows.

La puerta **falla ante cualquier aviso que no esté en esa lista**, y lista los aceptados en cada
ejecución para que no se conviertan en deuda invisible.

## Recomendaciones, por orden

1. Implementar las cabeceras de seguridad HTTP (H-1) — o documentar explícitamente que son
   responsabilidad del proxy y corregir SECURITY-STANDARD.md §7 para que no prometa lo que el
   framework no hace.
2. Añadir `pip-audit` y su puerta de calidad, cerrando la laguna de vulnerabilidades conocidas.
3. Decidir el valor por defecto de `trust_forwarded_headers` (H-2).
4. Corregir el comentario obsoleto (H-3) — trivial, solo documentación.

---

# Revisión de Sprint 3.0 (v0.10.0-alpha)

Revisión propia del sprint, sobre las cuatro superficies que ha tocado: cabeceras de reenvío,
credenciales y conexiones de Redis, secretos y mensajes de error de JWT, y CVEs transitivas.

## Resumen

| Área | Resultado |
|---|---|
| Spoofing e inyección de cabeceras | ✅ Cerrado con `api_trusted_proxies` ([ADR-011](architecture/adr/ADR-011-trusted-proxy-architecture.md)) |
| Credenciales de Redis | ✅ Sin secretos en código; TLS verificado por defecto |
| Fugas de conexión de Redis | ✅ Ninguna conexión sobrevive al apagado — verificado contra un Redis real |
| Secretos débiles de JWT | ✅ Mínimo por algoritmo, validado al arrancar |
| Mensajes de error de JWT | ✅ No revelan el secreto |
| CVEs transitivas | ✅ `pip-audit` limpio, **0 excepciones aceptadas** |

**Ningún hallazgo abierto.** Dos limitaciones conocidas, ambas documentadas y en el backlog — no
son hallazgos porque son decisiones tomadas a conciencia, no descuidos.

## 1. Spoofing e inyección de cabeceras

**Antes**: `X-Forwarded-For` se creía viniera de donde viniera. Un cliente que rotase la cabecera
estrenaba cubo de rate limiting en cada petición.

**Ahora**: la confianza se decide contra la **IP de la conexión TCP**, el único dato de la petición
que el cliente no puede falsificar. Verificado en
[`tests/unit/test_forwarded_headers_trust.py`](../tests/unit/test_forwarded_headers_trust.py) con
los cinco casos del modelo de amenaza: spoofing directo, proxy de confianza, proxy no confiable,
cadena de varios proxies y lista vacía.

Dos propiedades que conviene destacar porque son fáciles de implementar mal:

- **La cadena se recorre de derecha a izquierda.** Tomar la entrada más a la izquierda —la lectura
  ingenua— es leer exactamente el trozo que un atacante puede anteponer. Es un fallo real que TEAF
  tenía.
- **Falla cerrado**: una entrada inválida en la lista aborta el arranque. Una lista de confianza
  con una errata descartada en silencio da una falsa sensación de protección.

**Riesgo residual**: sin configurar `api_trusted_proxies`, el comportamiento es el de v0.9.2-alpha.
El sprint aporta la posibilidad de configurarlo correctamente, no un valor por defecto distinto —
el razonamiento sigue siendo el de [ADR-010 §4](architecture/adr/ADR-010-security-headers-and-forwarded-trust.md)
y se documenta en [SECURITY-CONFIGURATION.md](security/SECURITY-CONFIGURATION.md).

## 2. Credenciales y conexiones de Redis

**Credenciales**: ninguna en código. La URL —que suele llevarlas embebidas— se toma de
`CACHE_REDIS_URL` o de un gestor de secretos. `RedisCacheConfiguration.url` tiene un valor por
defecto local (`redis://localhost:6379/0`) sin credenciales, que es inservible en producción a
propósito: no hay forma de desplegar con una credencial por defecto.

**Verificado**: `grep` sobre el árbol confirma que ninguna URL con credenciales entra en el
repositorio, y el campo está marcado `sensitive=True` en el manifiesto del módulo, de modo que no
se emite en `runtime.manifest.json` ni en `/runtime/configuration`.

**TLS**: `tls_verify` es `True` por defecto. Solo se pasa a la conexión cuando la URL es
`rediss://`, porque `ssl_cert_reqs` únicamente lo acepta `SSLConnection` — pasarlo sobre
`redis://` reventaba con `TypeError`, lo que se corrigió en este sprint (ver *Fixed* del
CHANGELOG). Desactivar la verificación queda documentado como algo que solo tiene sentido contra un
Redis de desarrollo con certificado autofirmado.

**Fugas de conexión**: el criterio de bloqueo del sprint era que ninguna conexión sobreviviera al
apagado. Verificado de tres formas:

1. `CacheModule.dispose()` llama a `provider.disconnect()`, simétrico con `start()`.
2. `disconnect()` es idempotente y suelta el cliente (`self._client = None`), de modo que un
   segundo apagado no falla ni deja el objeto en un estado ambiguo.
3. [`tests/integration/test_cache_redis.py`](../tests/integration/test_cache_redis.py) lo comprueba
   **contra un Redis real**: `health_check()` devuelve `False` tras `disconnect()`.

Los tres almacenes distribuidos **no abren conexiones propias**: reciben un `CacheProvider` cuyo
ciclo de vida lleva el módulo. Es lo que hace que solo haya un sitio del que preocuparse.

## 3. Secretos y mensajes de error de JWT

**Mínimo derivado del algoritmo**, no inventado: RFC 7518 §3.2 exige que la clave HMAC sea al menos
del tamaño de la salida del hash. Se valida **al arrancar** —en `Settings` y en
`JWTProvider.__init__`—, nunca durante una petición.

**Los mensajes de error no revelan el secreto.** Comprobado explícitamente en
[`tests/unit/test_jwt_secret_policy.py`](../tests/unit/test_jwt_secret_policy.py) y también desde
el lado del consumidor en la aplicación de referencia: el mensaje nombra algoritmo, longitud
recibida y longitud exigida. Un error que filtrase el secreto a los logs sería peor que el propio
secreto débil.

**Ruptura asumida**: una aplicación con un secreto por debajo del mínimo deja de arrancar. Es
deliberado. Seguir aceptándolo en silencio sería debilitar la política para mantener
compatibilidad, que es justo lo que un cierre de hallazgo de seguridad no debe hacer.

## 4. CVEs transitivas

`python scripts/check_dependency_audit.py` → **0 vulnerabilidades, 0 excepciones aceptadas**.

Las 7 entradas de `starlette` que Sprint 2.9.2 tuvo que aceptar —bloqueadas por el pin
`starlette<0.42.0` de `fastapi 0.115.6`— desaparecen con la actualización a `fastapi 0.141.1` /
`starlette 1.4.1`. Las entradas se **eliminan** del fichero en vez de dejarse marcadas como
aceptadas: una excepción caducada es deuda invisible, porque la próxima vulnerabilidad de ese
paquete pasaría desapercibida bajo una justificación que ya no aplica.

`redis` entra en el árbol de dependencias como extra opcional y queda dentro del alcance de la
puerta: sus futuras CVEs harán fallar la auditoría igual que las de cualquier otra.

## Limitaciones conocidas (no son hallazgos)

| Limitación | Por qué se acepta |
|---|---|
| `RedisQuotaStore.consume` no es atómico: dos réplicas concurrentes admiten un ligero exceso sobre la cuota | Documentado en su docstring, en [CACHE.md §10](modules/cache/CACHE.md) y en el backlog. Un exceso ocasional acotado es un problema mucho menor que una cuota multiplicada por el número de réplicas. Resolverlo exige un script Lua o `INCRBYFLOAT` con semántica distinta — cambio de diseño, no arreglo |
| Sin `api_trusted_proxies` configurado, las cabeceras de reenvío se siguen creyendo | Invertir el valor por defecto rompería silenciosamente todo despliegue correcto tras un proxy ([ADR-010 §4](architecture/adr/ADR-010-security-headers-and-forwarded-trust.md), [ADR-011 §5](architecture/adr/ADR-011-trusted-proxy-architecture.md)) |

## Recomendaciones para Sprint 3.1

1. Hacer atómico `RedisQuotaStore.consume`.
2. Revisar si, con `api_trusted_proxies` ya disponible y documentado, procede invertir el valor por
   defecto de `trust_forwarded_headers` en una versión mayor — con guía de migración.
3. Soportar `Forwarded` (RFC 7239) además de `X-Forwarded-For`.
