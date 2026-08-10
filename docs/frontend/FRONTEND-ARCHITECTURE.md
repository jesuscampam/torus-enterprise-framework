# Arquitectura del frontend — TEAF

Documento de referencia de la base de frontend del framework. La decisión de stack y su
justificación están en [ADR-013](../architecture/adr/ADR-013-enterprise-frontend-stack.md); este
documento describe **cómo está construido** lo que esa decisión habilitó.

Entregado en Sprint 3.5a (*core*). Alcance: shell arrancable, cliente API tipado y autenticación.

## 1. Capas y dirección de dependencias

La misma regla no negociable que en backend ([ARCHITECTURE.md](../architecture/ARCHITECTURE.md)):
**una capa nunca importa una capa más externa que ella**.

```
pages/  ──────┐
components/ ──┼──> hooks/ ──> store/ ──> services/ ──> config/
              │                              │
              └──────────────────────────────┴──> types/
```

| Capa | Responsabilidad | No puede |
|---|---|---|
| `pages/` | Vistas a nivel de ruta. | Llamar a `fetch` directamente. |
| `components/` | UI reutilizable. | Conocer rutas de API. |
| `hooks/` | Lógica reutilizable de React; fachada sobre el store. | Contener JSX de pantalla. |
| `store/` | Estado **de cliente** (sesión, preferencias). | Guardar respuestas de la API. |
| `services/` | HTTP, autenticación, almacenamiento de tokens. | Importar componentes o hooks. |
| `types/` | Espejo de los contratos del backend. | Contener lógica. |
| `config/` | Configuración por entorno. | Contener secretos. |

### La dependencia circular y cómo se resuelve

El cliente HTTP necesita el access token y saber renovarlo; quien tiene ambas cosas es el store,
que a su vez usa el cliente para hacer login. Resolverlo importando uno desde el otro crearía un
ciclo.

La solución es la de backend: **el de dentro define el contrato, el de fuera lo satisface**.
`services/http/session.ts` expone un `SessionBridge` sin dependencias; el `HttpClient` lo consume y
el store se registra en él al arrancar. Ningún módulo importa al otro.

## 2. Cliente API

`services/http/client.ts` concentra las cuatro cosas que, si no, acaban copiadas en cada llamada:

| Responsabilidad | Detalle |
|---|---|
| **Correlación** | Genera un `X-Correlation-Id` por petición — misma cabecera que `HEADER_CORRELATION_ID` en backend. Permite cruzar un error del navegador con su traza en los logs del servidor. |
| **Autenticación** | Adjunta `Authorization: Bearer <token>` cuando hay sesión. |
| **Errores** | Traduce la respuesta a `ApiError`, conservando el Problem Details (RFC 7807) del backend — [API-STANDARD.md §6](../standards/API-STANDARD.md). Si un intermediario (proxy, balanceador) devuelve HTML, sintetiza uno equivalente. |
| **Timeout** | `AbortSignal.timeout`, combinable con el signal del llamante. |

### Renovación de sesión (*single-flight*)

Ante un 401 el cliente llama a `refreshAccessToken` y reintenta la petición original una sola vez.
Si varias peticiones reciben 401 a la vez, **comparten una única renovación**. Sin eso, una pantalla
con cuatro peticiones en paralelo dispararía cuatro refrescos simultáneos y, como el backend rota
los refresh tokens al usarlos (`JWTTokenProvider.refresh`), tres de ellos fallarían.

## 3. Autenticación

### Por qué las rutas son configurables

**TEAF no expone endpoints de login.** El framework entrega primitivas —`JWTTokenProvider`,
`IdentityProvider`, `SecurityMiddleware`, RBAC ([ADR-007](../architecture/adr/ADR-007-enterprise-security-stack.md))—
pero ninguna ruta `/auth/login`: eso es de la aplicación, no del framework.

Por eso `AuthService` recibe las rutas por constructor, alimentadas desde `config/`. El mismo módulo
sirve a TicketGateway, Portal NOC y Portal SRE aunque publiquen rutas distintas.

### Contratos consumidos

| Concepto | Forma | Origen en backend |
|---|---|---|
| Login / refresh | `{accessToken, refreshToken, tokenType, expiresIn}` | `TokenPair.as_dict()` |
| Sesión actual | `Principal` = identidad + roles + permisos + tenant | modelo de dominio de seguridad |

### Almacenamiento de tokens

Contrato `TokenStorage` con dos implementaciones — mismo patrón provider que `CacheProvider`
([ADR-012](../architecture/adr/ADR-012-redis-optional-infrastructure.md)):

| Implementación | Riesgo XSS | Sobrevive a recarga | Cuándo |
|---|---|---|---|
| `MemoryTokenStorage` (**por defecto**) | Nada que robar | No | Arranque seguro. |
| `LocalStorageTokenStorage` | Legible por cualquier script | Sí | Opt-in explícito vía `VITE_PERSIST_SESSION`. |

El defecto es el seguro; persistir es una decisión que la aplicación escribe
([SECURITY-STANDARD.md §2](../standards/SECURITY-STANDARD.md)).

### Ciclo de sesión

```
arranque ──> restore()  ──(sin tokens)──> anonymous
                └──(con tokens)──> GET me ──(200)──> authenticated
                                        └──(401)──> limpia y queda anonymous

login() ──> POST login ──> guarda tokens ──> GET me ──> authenticated
                                   └── si falla cualquiera de los dos: anonymous

petición con 401 ──> refresh ──(ok)──> reintenta
                        └──(falla)──> cierra sesión
```

Una sesión nunca queda a medias: si hay tokens pero no se pudo obtener el `Principal`, el estado
vuelve a `anonymous`. Con tokens pero sin roles, la aplicación no sabría qué puede hacer el usuario.

## 4. Autorización de interfaz

`ProtectedRoute` admite `requiredRole` y `requiredPermission`, y mientras la sesión se está
restaurando **no decide**: muestra un indicador de carga. Redirigir en ese instante expulsaría a un
usuario con sesión válida solo por llegar antes que la respuesta del backend.

> **Es complemento, no sustituto.** Esconder un enlace no protege un endpoint. La comprobación que
> manda es la del servidor.

## 5. Configuración por entorno

`config/index.ts` lee variables `VITE_` con valores por defecto seguros — equivalente cliente de
`teaf/_internal/config/` y aplicación de *Configuration by Environment*
([ADR-005](../architecture/adr/ADR-005-cloud-ready.md)).

**Todo lo que llega aquí es público**: queda incrustado en el bundle y es legible desde las
DevTools. Nunca un secreto. La plantilla completa está en `frontend/.env.example`.

## 6. Pruebas

Vitest + Testing Library, con la configuración compartida con Vite (un solo `vite.config.ts`).
44 pruebas en Sprint 3.5a:

| Área | Qué cubre |
|---|---|
| `services/http/client.test.ts` | Correlación única por petición, Bearer, traducción de Problem Details, 204 sin cuerpo, query params, y los cuatro caminos de renovación incluido el *single-flight*. |
| `services/auth/tokenStorage.test.ts` | Ambas implementaciones, incluido JSON corrupto, datos de versiones anteriores y cuota llena. |
| `store/authStore.test.ts` | Login correcto y fallido, sesión a medias, logout, rehidratación, roles/permisos y el manejador de refresco. |
| `components/ProtectedRoute.test.tsx` | Redirección, espera durante la restauración y las cuatro combinaciones de rol/permiso. |

Se prueba **comportamiento observable**, no detalles de implementación — misma exigencia que
[CODING-STANDARD.md](../standards/CODING-STANDARD.md) impone en backend.

## 7. Pendiente

| Sprint | Alcance |
|---|---|
| 3.5b | Librería de componentes: tablas de datos, formularios, navegación. |
| 3.5c | Paleta corporativa TORUS, variantes por producto, modo oscuro. |
| — | Pruebas E2E del flujo completo contra un backend real; hoy la cobertura llega hasta la integración con dobles. |
