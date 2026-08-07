# Estándar de Seguridad — TEAF

Este documento define las prácticas de seguridad obligatorias del framework, en cumplimiento del principio **Security by Design**. Aplica a toda aplicación construida sobre TEAF, sin excepciones.

> Este documento sigue siendo la fuente normativa de *qué* prácticas son obligatorias. *Cómo* TEAF las implementa concretamente (Sprint 2.7, `teaf.security`) está documentado en [docs/security/SECURITY-ARCHITECTURE.md](../security/SECURITY-ARCHITECTURE.md) y sus documentos relacionados (JWT.md, APIKEY.md, LDAP.md, AZURE-AD.md, RBAC.md, CLAIMS.md) — no se duplica aquí.

## 1. Autenticación (JWT)

> Implementado por `teaf.security.JWTProvider` — ver [JWT.md](../security/JWT.md).

- Toda API protegida exige un **JWT** válido, verificado por `middleware/` antes de que la petición llegue a `api/`.
- Se emiten dos tipos de token:
  - **Access token**: de vida corta (recomendado 15 minutos), usado en cada petición vía header `Authorization: Bearer <token>`.
  - **Refresh token**: de vida más larga, almacenado de forma segura (httpOnly cookie o almacenamiento seguro del cliente), usado exclusivamente para obtener nuevos access tokens.
- Los tokens se firman con algoritmos asimétricos (RS256) o HMAC con secreto robusto (HS256) gestionado vía secretos de entorno, nunca hardcodeado.
- La revocación de sesión se implementa mediante lista de revocación o rotación de refresh tokens; un refresh token usado más de una vez se considera comprometido y revoca toda la cadena de sesión.

## 2. Autorización (RBAC)

> Implementado por `teaf.security` (`@authorize()`, `StaticRoleResolver`, `PrincipalResolver`, `Policy`) — ver [RBAC.md](../security/RBAC.md).

- El modelo de autorización estándar es **RBAC** (Role-Based Access Control): usuarios → roles → permisos.
- La verificación de autorización ocurre en `security/`, invocada desde `api/` o `services/` según el nivel de granularidad (ruta vs. recurso específico), nunca implementada de forma ad-hoc y duplicada en cada endpoint.
- El principio de **mínimo privilegio** rige el diseño de roles: ningún rol se define con permisos más amplios de los estrictamente necesarios.

## 3. Gestión de contraseñas y credenciales

> Implementado por `teaf.security.Argon2PasswordHasher`/`BcryptPasswordHasher` — ver [SECURITY-ARCHITECTURE.md](../security/SECURITY-ARCHITECTURE.md).

- Las contraseñas se almacenan exclusivamente como hash con **bcrypt** o **argon2** (nunca SHA/MD5, nunca en texto plano).
- Las credenciales de infraestructura (base de datos, integraciones SAP/Salesforce/Control-M, claves de IA) se gestionan vía variables de entorno resueltas por `config/`, respaldadas en producción por un gestor de secretos (Azure Key Vault).
- Ningún secreto se versiona en el repositorio; `.gitignore` excluye explícitamente `.env` y archivos de credenciales (ver raíz del repositorio).

## 4. Validación de entradas

- Toda entrada externa se valida mediante `schemas/` (Pydantic) en el borde del sistema (`api/`), antes de alcanzar `services/`.
- Los `webhooks/` entrantes verifican la firma/autenticidad del emisor (SAP, Salesforce, Control-M) antes de procesar el payload.
- Se aplica sanitización específica según el contexto de salida (HTML, SQL, shell) para prevenir inyección; el uso de queries parametrizadas vía SQLAlchemy es obligatorio — se prohíbe la construcción de SQL por concatenación de strings.

## 5. CORS

- La política CORS se configura explícitamente por entorno (`config/`), permitiendo únicamente los orígenes conocidos (frontend propio, integraciones autorizadas); se prohíbe `Access-Control-Allow-Origin: *` en cualquier entorno con datos reales.

## 6. Mitigación OWASP Top 10

TEAF exige mitigación explícita, a nivel de framework, de:

| Riesgo OWASP | Mitigación en TEAF |
|---|---|
| Broken Access Control | RBAC centralizado en `security/`, verificado en cada capa relevante. |
| Cryptographic Failures | TLS obligatorio en tránsito; hashing fuerte en reposo; sin secretos en código. |
| Injection | ORM parametrizado (SQLAlchemy); validación estricta vía `schemas/`. |
| Insecure Design | Security by Design como principio arquitectónico desde el ADR inicial. |
| Security Misconfiguration | Configuración por entorno (`config/`), sin defaults inseguros en producción. |
| Vulnerable Components | Escaneo de dependencias en CI (GitHub Actions, ver Versión 5 del roadmap). |
| Identification/Auth Failures | JWT con expiración corta, rotación de refresh tokens, RBAC. |
| Software/Data Integrity Failures | Verificación de firma en `webhooks/`; imágenes Docker desde fuentes controladas. |
| Logging/Monitoring Failures | Logging estructurado obligatorio (ver `LOGGING-STANDARD.md`) y observabilidad OpenTelemetry. |
| SSRF | Validación estricta de URLs/destinos en integraciones salientes (`webhooks/`, `ai/`). |

## 7. Headers de seguridad HTTP

Toda respuesta HTTP incluye, como mínimo: `Strict-Transport-Security`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` (o CSP equivalente), `Content-Security-Policy` apropiada para el frontend servido.

**Lo implementa el framework**, no el proxy: desde Sprint 2.9.2, `SecurityHeadersMiddleware` (`teaf/_internal/middleware/security_headers.py`) las emite en toda respuesta, gobernado por `Settings` y instalado siempre por `create_app`. El reparto de responsabilidad con el proxy inverso / WAF está decidido en [ADR-010](../architecture/adr/ADR-010-security-headers-and-forwarded-trust.md).

| Cabecera | Valor por defecto | Configuración | Cuándo se emite |
|---|---|---|---|
| `X-Content-Type-Options` | `nosniff` | — | Siempre |
| `X-Frame-Options` | `DENY` | `security_frame_options` (vacío la omite) | Siempre |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'` | `security_content_security_policy` | Salvo en `/docs` y `/redoc` |
| `Strict-Transport-Security` | `max-age=31536000` | `security_hsts_max_age_seconds` (`0` la omite) | **Solo sobre HTTPS** (RFC 6797 §7.2) |

`security_headers_enabled: bool = True` las activa todas; a `False` no se emite ninguna.

Tres matices que hay que conocer antes de confiar en esta tabla:

- **HSTS solo viaja sobre HTTPS**, como exige RFC 6797 §7.2. Detrás de un proxy que termina TLS, la aplicación debe recibir el esquema correcto (uvicorn `--proxy-headers`), o no se emitirá.
- **La CSP no se aplica a `/docs` ni `/redoc`**: Swagger UI y ReDoc cargan sus propios recursos y `default-src 'none'` los dejaría en blanco. El resto de cabeceras sí se aplican también ahí.
- **La CSP por defecto es la de una API JSON, no la de un frontend.** Una aplicación TEAF que sirva HTML propio **debe** sustituirla por la política de su frontend; la de por defecto le impedirá cargar cualquier recurso.

El middleware **nunca sobrescribe** una cabecera que la aplicación o el proxy ya hayan establecido, así que añadirlas también en el borde no genera conflicto.

## 8. Logging de auditoría

- Toda acción de autenticación (login, logout, fallo de login), cambio de permisos, y operación destructiva (baja lógica, eliminación) se registra en un log de auditoría inmutable, correlacionado con el usuario y el `correlationId` (ver `LOGGING-STANDARD.md`).
- El log de auditoría nunca contiene la contraseña ni el token completo del usuario.

## 9. Cifrado en tránsito y en reposo

- Toda comunicación externa (cliente-API, API-integraciones) se realiza exclusivamente sobre TLS.
- Los datos sensibles en reposo (por ejemplo, tokens de integración con SAP/Salesforce almacenados) se cifran a nivel de columna o se delegan a un gestor de secretos, nunca se almacenan en texto plano en PostgreSQL.

## 10. Principio de mínimo privilegio (infraestructura)

- Las credenciales de servicio (backend → base de datos, backend → integraciones) usan el mínimo permiso necesario para su función, nunca cuentas con privilegios administrativos compartidas entre componentes.
