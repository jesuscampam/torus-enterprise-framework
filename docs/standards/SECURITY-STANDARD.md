# Estándar de Seguridad — TEAF

Este documento define las prácticas de seguridad obligatorias del framework, en cumplimiento del principio **Security by Design**. Aplica a toda aplicación construida sobre TEAF, sin excepciones.

## 1. Autenticación (JWT)

- Toda API protegida exige un **JWT** válido, verificado por `middleware/` antes de que la petición llegue a `api/`.
- Se emiten dos tipos de token:
  - **Access token**: de vida corta (recomendado 15 minutos), usado en cada petición vía header `Authorization: Bearer <token>`.
  - **Refresh token**: de vida más larga, almacenado de forma segura (httpOnly cookie o almacenamiento seguro del cliente), usado exclusivamente para obtener nuevos access tokens.
- Los tokens se firman con algoritmos asimétricos (RS256) o HMAC con secreto robusto (HS256) gestionado vía secretos de entorno, nunca hardcodeado.
- La revocación de sesión se implementa mediante lista de revocación o rotación de refresh tokens; un refresh token usado más de una vez se considera comprometido y revoca toda la cadena de sesión.

## 2. Autorización (RBAC)

- El modelo de autorización estándar es **RBAC** (Role-Based Access Control): usuarios → roles → permisos.
- La verificación de autorización ocurre en `security/`, invocada desde `api/` o `services/` según el nivel de granularidad (ruta vs. recurso específico), nunca implementada de forma ad-hoc y duplicada en cada endpoint.
- El principio de **mínimo privilegio** rige el diseño de roles: ningún rol se define con permisos más amplios de los estrictamente necesarios.

## 3. Gestión de contraseñas y credenciales

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

## 8. Logging de auditoría

- Toda acción de autenticación (login, logout, fallo de login), cambio de permisos, y operación destructiva (baja lógica, eliminación) se registra en un log de auditoría inmutable, correlacionado con el usuario y el `correlationId` (ver `LOGGING-STANDARD.md`).
- El log de auditoría nunca contiene la contraseña ni el token completo del usuario.

## 9. Cifrado en tránsito y en reposo

- Toda comunicación externa (cliente-API, API-integraciones) se realiza exclusivamente sobre TLS.
- Los datos sensibles en reposo (por ejemplo, tokens de integración con SAP/Salesforce almacenados) se cifran a nivel de columna o se delegan a un gestor de secretos, nunca se almacenan en texto plano en PostgreSQL.

## 10. Principio de mínimo privilegio (infraestructura)

- Las credenciales de servicio (backend → base de datos, backend → integraciones) usan el mínimo permiso necesario para su función, nunca cuentas con privilegios administrativos compartidas entre componentes.
