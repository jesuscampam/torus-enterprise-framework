# ADR-013 — Stack de arranque del frontend empresarial

## Estado

**Aceptado** — Sprint 3.5a (Versión 3, *Frontend Foundation*).

Añade a [STACK.md](../STACK.md) cinco piezas de frontend —Vite, React Router, Zustand, TanStack
Query y Vitest— según exige CLAUDE.md §4 («ninguna tecnología fuera de esta lista se introduce sin
un ADR aprobado»).

## Contexto

[STACK.md](../STACK.md) aprueba **React + TypeScript** y **Material UI**, y nada más del lado
cliente. En su propio apartado de trade-offs lo reconoce explícitamente:

> «mayor responsabilidad del equipo en decisiones de arquitectura frontend (routing, estado) frente
> a frameworks más opinados como Angular; se mitiga fijando convenciones propias».

Ese «se mitiga fijando convenciones propias» es una deuda que hasta hoy nadie había pagado. React no
trae empaquetador, ni enrutador, ni gestión de estado, ni ejecutor de pruebas: son cuatro decisiones
que hay que tomar sí o sí antes de escribir la primera línea, y que en la práctica **no se pueden
revertir barato** una vez que veinte pantallas dependen de ellas.

Hasta este Sprint, `frontend/` contenía diez `README.md` describiendo responsabilidades por carpeta
y cero líneas de código. La Épica 3 del [BACKLOG](../../roadmap/BACKLOG.md) pide shell de
aplicación, theming, autenticación JWT, cliente API tipado, componentes base y estado global. Nada
de eso puede empezar sin resolver antes estas cuatro elecciones.

### Dos restricciones que vienen del backend y condicionan el diseño

**1. TEAF no expone endpoints de login.** El framework entrega primitivas de seguridad
(`JWTTokenProvider`, `IdentityProvider`, `SecurityMiddleware`, RBAC) pero ninguna ruta
`/auth/login` — coherente con [ADR-007](ADR-007-enterprise-security-stack.md) y con que TEAF es un
framework, no una aplicación. Las rutas concretas las define cada aplicación.

Consecuencia directa: **el cliente de autenticación del frontend no puede cablear rutas**. Tiene que
recibirlas por configuración, igual que el backend recibe proveedores por inyección.

**2. Los contratos ya existen y hay que respetarlos, no reinventarlos.** El frontend consume lo que
el backend ya emite:

| Contrato backend | Origen | Forma |
|---|---|---|
| Respuesta de login | `TokenPair.as_dict()` (`teaf/_internal/security/models.py`) | `{accessToken, refreshToken, tokenType, expiresIn}` |
| Errores | [API-STANDARD.md §6](../../standards/API-STANDARD.md) | RFC 7807 Problem Details, con `correlationId` obligatorio |
| Colecciones | [API-STANDARD.md §4](../../standards/API-STANDARD.md) | Sobre `{data, meta:{page,pageSize,totalItems,totalPages}}` |
| Correlación | `HEADER_CORRELATION_ID` (`teaf/_internal/shared/constants.py`) | Cabecera `X-Correlation-Id` |
| Versionado | [API-STANDARD.md §2](../../standards/API-STANDARD.md) | Prefijo `/api/v1` |

Es la aplicación literal del principio **API First** ([ADR-004](ADR-004-api-first.md)): el contrato
ya está definido; el cliente se alinea a él.

## Problema

Elegir empaquetador, enrutador, gestión de estado y ejecutor de pruebas para un frontend que debe
sostener **todas** las aplicaciones TORUS futuras durante varios años, sin caer en ninguno de los
dos errores habituales:

- **Sobre-ingeniería**: montar Redux + sagas + un cliente GraphQL para pantallas que solo listan y
  editan registros. CLAUDE.md §3 lo prohíbe explícitamente.
- **Infra-ingeniería**: dejar que cada aplicación elija por su cuenta, que es exactamente la deuda
  que este ADR viene a saldar.

## Decisión

### 1. Vite como empaquetador y servidor de desarrollo

| Candidato | Por qué no |
|---|---|
| Create React App | Sin mantenimiento activo desde 2023; los propios docs de React ya no lo recomiendan. |
| Next.js | Aporta SSR y rutas por fichero, pero **exige un proceso Node en producción**. El destino declarado en [ADR-005](ADR-005-cloud-ready.md) es Azure App Service sirviendo estáticos tras el backend FastAPI; pagar un runtime Node por SSR que ninguna aplicación interna de TORUS ha pedido es coste sin contrapartida. |
| Webpack a mano | Configuración propia que alguien tendrá que mantener durante años. |

**Vite**: build de producción con Rollup, servidor de desarrollo con HMR sobre módulos ES nativos,
soporte TypeScript de fábrica y salida estática pura desplegable en cualquier sitio. Comparte
configuración con Vitest, lo que elimina la duplicación clásica entre config de build y config de
tests.

### 2. React Router como enrutador

Estándar de facto del ecosistema React sin framework. Las alternativas serias (TanStack Router) son
más jóvenes y su ventaja principal —rutas con tipado estricto— no compensa hoy la diferencia de
madurez y de talento disponible, que es precisamente el criterio con el que STACK.md justificó
React.

### 3. Zustand **y** TanStack Query — dos piezas porque son dos problemas

Esto no es redundancia; es la distinción que más deuda genera cuando se ignora:

- **Estado de servidor**: datos que viven en el backend y de los que el navegador solo tiene una
  copia potencialmente obsoleta. Necesita caché, revalidación, deduplicación de peticiones en vuelo,
  reintentos y estados de carga/error. → **TanStack Query**.
- **Estado de cliente**: datos que solo existen en el navegador (sesión en curso, tema activo,
  estado del menú lateral). Necesita un contenedor simple y suscripción granular. → **Zustand**.

Meter el estado de servidor en un store global es el antipatrón que produce los `useEffect` que
llaman a `fetch`, escriben en el store, y dejan a mano la invalidación de la caché. Redux Toolkit +
RTK Query cubriría ambos con una sola pieza, pero a cambio de un volumen de boilerplate
(slices, thunks, providers) que contradice el KISS de CLAUDE.md §3 para el tipo de aplicación que
TORUS va a construir: portales internos con formularios, tablas y flujos de aprobación.

Zustand son ~1 KB y una función; TanStack Query resuelve el problema de caché que nadie debería
reimplementar.

### 4. Vitest + Testing Library como pruebas

Vitest reutiliza la configuración de Vite (un solo `vite.config.ts` para build y tests, sin
duplicar alias ni transformaciones), su API es compatible con Jest y su ejecución es
sensiblemente más rápida sobre módulos ES. Testing Library aporta la disciplina de probar
**comportamiento observable** en vez de detalles de implementación, que es la misma exigencia que
[CODING-STANDARD.md](../../standards/CODING-STANDARD.md) impone en backend.

### 5. Almacenamiento de tokens: abstracción, no elección cableada

[SECURITY-STANDARD.md §2](../../standards/SECURITY-STANDARD.md) exige que el refresh token viva en
«httpOnly cookie o almacenamiento seguro del cliente». Cuál de los dos es correcto **depende de la
aplicación**, no del framework: una app tras un backend que emite cookies httpOnly no debería tocar
`localStorage`; un portal servido desde otro dominio no puede usarlas.

Por tanto el framework no elige: define el contrato `TokenStorage` y entrega dos implementaciones,
exactamente el mismo patrón provider que `CacheProvider` ([ADR-012](ADR-012-redis-optional-infrastructure.md))
y `SecretProvider` en backend:

| Implementación | Comportamiento | Cuándo |
|---|---|---|
| `MemoryTokenStorage` | Tokens solo en memoria del módulo. **Por defecto.** | Máxima resistencia a XSS: un script inyectado no encuentra nada que robar en `localStorage`. Se pierde la sesión al recargar. |
| `LocalStorageTokenStorage` | Persiste en `localStorage`. **Opt-in explícito.** | Cuando la aplicación acepta conscientemente el riesgo XSS a cambio de que la sesión sobreviva a la recarga. |

El defecto es el seguro. Persistir es una decisión que la aplicación toma escribiéndola.

## Consecuencias

### Positivas

- Las cuatro decisiones estructurales quedan tomadas **una vez**, con argumento escrito, para todas
  las aplicaciones TORUS futuras.
- El cliente API queda alineado por construcción a los contratos que el backend ya emite —
  Problem Details, sobre de colecciones, `X-Correlation-Id`— con lo que una traza de error cruza
  navegador y servidor sin trabajo adicional.
- La configurabilidad de rutas de auth permite que TicketGateway, Portal NOC y Portal SRE usen el
  mismo módulo de autenticación aunque expongan rutas distintas.
- `TokenStorage` deja la decisión de seguridad donde corresponde —la aplicación— sin que el
  framework imponga la opción arriesgada por defecto.
- Vitest comparte configuración con Vite: una sola fuente de verdad de alias y transformaciones.

### Negativas

- **Cinco dependencias nuevas** de un ecosistema que se mueve más rápido que el de Python. Se
  mitiga fijando versiones exactas (misma política que `requirements.txt`) y con Dependabot ya
  configurado en `.github/`.
- **Dos piezas de estado en lugar de una.** Exige que quien llegue nuevo entienda la distinción
  servidor/cliente. Se mitiga documentándola en `frontend/src/store/README.md` y en
  `docs/frontend/FRONTEND-ARCHITECTURE.md`.
- **Renunciamos a SSR.** Si alguna aplicación futura necesitara renderizado en servidor por SEO
  —improbable en portales internos autenticados— habría que reabrir esta decisión con un ADR nuevo.
- **React Router acopla al ecosistema React** de una forma que un cambio de librería de UI no
  arrastraría. Es coste asumido: React ya está decidido en STACK.md.
- El defecto `MemoryTokenStorage` implica que **la sesión se pierde al recargar** mientras la
  aplicación no active persistencia. Es intencionado: preferimos que el arranque sea seguro y que
  relajar la seguridad sea un acto explícito.

## Alcance de este ADR

Cubre el arranque (Sprint 3.5a): empaquetador, enrutador, estado, pruebas, cliente API y
autenticación. **No decide** librería de formularios, de tablas de datos ni de gráficas — se
resolverán cuando la librería de componentes (Sprint 3.5b) demuestre necesitarlas, no antes
(CLAUDE.md §3: «no se introduce abstracción sin una necesidad concreta y actual»).
