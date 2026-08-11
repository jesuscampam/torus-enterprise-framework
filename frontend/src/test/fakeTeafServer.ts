/**
 * Doble de un backend TEAF, montado a la altura de `fetch`.
 *
 * Se doblan las **peticiones de red**, no el `HttpClient`: así el recorrido de
 * las pruebas de flujo atraviesa el cliente real —correlación, `Authorization`,
 * traducción de errores RFC 7807, timeout— en lugar de saltárselo. Doblar el
 * cliente probaría que las pantallas llaman a un doble, que es justo lo que no
 * interesa saber.
 *
 * Las cargas útiles reproducen la forma que emite el TEAF real, verificada por
 * `tests/e2e/test_frontend_api_contract.py`. Esa prueba es lo que impide que
 * este doble se convierta en ficción: si el backend cambiara una respuesta,
 * falla allí y hay que actualizar aquí.
 *
 * **Los endpoints de autenticación no son de TEAF.** El framework no expone
 * login (ADR-013 §3): entrega primitivas de seguridad y cada aplicación publica
 * sus rutas. Aquí se simula la aplicación anfitriona, no el framework.
 */
import { config } from '@/config';

/** Credenciales que el backend simulado acepta. */
export const VALID_CREDENTIALS = { username: 'ada', password: 'secreto' };

const ACCESS_TOKEN = 'access-token-1';
const REFRESH_TOKEN = 'refresh-token-1';

/** `Principal` devuelto por el endpoint de sesión de la aplicación anfitriona. */
export const PRINCIPAL = {
  identity: {
    id: 'u-1',
    providerId: 'jwt',
    claims: { subject: 'u-1', name: 'Ada Lovelace' },
    authenticated: true,
  },
  roles: ['operator'],
  permissions: ['runtime:read'],
};

/** `GET /health` — misma forma que emite `teaf.Application()`. */
export const HEALTH = {
  status: 'ok',
  name: 'TEAF',
  version: '0.10.3-alpha',
  environment: 'development',
  buildDate: 'unknown',
  modules: { status: 'healthy', checks: {} },
};

/** `GET /runtime/info`. */
export const RUNTIME_INFO = {
  runtimeId: 'f7c280c3-89a2-4a0f-a300-f0a52814c92d',
  startupTime: '2026-08-11T09:00:00+00:00',
  runningTimeSeconds: 125.5,
  registeredModules: 5,
  registeredServices: 0,
  registeredCapabilities: 0,
  registeredPlugins: 0,
  registeredFeatures: 0,
  frameworkVersion: '0.10.3-alpha',
  pythonVersion: '3.11.15',
  configurationSummary: { appName: 'TEAF', environment: 'development' },
  dependencyGraphSummary: { nodes: 5, edges: 1 },
  containerStatistics: { registeredContracts: 0 },
  memoryRssBytes: 83333120,
  cpuTimeSeconds: 1.8,
};

/** Un descriptor de `GET /runtime/modules`, con los 16 campos reales. */
function moduleDescriptor(name: string, dependencies: string[] = []) {
  return {
    id: name,
    name,
    version: '0.10.3-alpha',
    author: null,
    description: '',
    status: 'contracts_only',
    lifecycleState: 'registered',
    capabilities: [],
    dependencies,
    tags: [],
    documentation: null,
    experimental: false,
    createdAt: '2026-08-11T09:00:00+00:00',
    updatedAt: '2026-08-11T09:00:00+00:00',
  };
}

/** Los cinco módulos de infraestructura que registra una `Application` estándar. */
export const RUNTIME_MODULES = [
  moduleDescriptor('database'),
  moduleDescriptor('storage'),
  moduleDescriptor('ai', ['security']),
  moduleDescriptor('scheduler'),
  moduleDescriptor('notification'),
];

/** `GET /runtime/events` — historial publicado durante el arranque. */
export const RUNTIME_EVENTS = [
  { name: 'framework.started', payload: {} },
  { name: 'framework.startup.completed', payload: {} },
];

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/** Problem Details RFC 7807, como los emite el manejador de errores de TEAF. */
function problem(status: number, title: string, correlationId: string | null): Response {
  return new Response(
    JSON.stringify({
      type: `https://teaf.torus/errors/http-${status}`,
      title,
      status,
      detail: title,
      correlationId: correlationId ?? 'generado-por-el-servidor',
    }),
    { status, headers: { 'Content-Type': 'application/problem+json' } }
  );
}

export interface FakeServerOptions {
  /** Fuerza un fallo en las rutas indicadas, para ejercitar el estado de error. */
  failing?: string[];
  /** Devuelve colecciones vacías, para ejercitar el estado vacío. */
  emptyCollections?: boolean;
}

export interface FakeServer {
  /** Reemplazo de `fetch` que se instala como global. */
  fetch: (input: string | URL | Request, init?: RequestInit) => Promise<Response>;
  /** Rutas solicitadas, en orden, para comprobar qué consultó la aplicación. */
  readonly requests: { path: string; method: string; correlationId: string | null }[];
  /** `true` mientras la sesión simulada siga abierta. */
  readonly hasSession: () => boolean;
}

/**
 * Construye el doble del backend.
 *
 * Exige `Authorization: Bearer` en todo lo que no sea autenticación: sin eso,
 * el recorrido «entrar y ver el panel» pasaría igual sin haber iniciado sesión,
 * y dejaría de demostrar nada.
 */
export function createFakeTeafServer(options: FakeServerOptions = {}): FakeServer {
  const { failing = [], emptyCollections = false } = options;
  const requests: { path: string; method: string; correlationId: string | null }[] = [];
  let sessionOpen = false;

  const collection = <T>(items: T[]): T[] => (emptyCollections ? [] : items);

  /** Extrae la URL sin depender de la conversión implícita de `Request`/`URL`. */
  function urlOf(input: string | URL | Request): string {
    if (typeof input === 'string') return input;
    return input instanceof URL ? input.href : input.url;
  }

  function respond(input: string | URL | Request, init: RequestInit): Response {
    const [rawPath = '', queryString] = urlOf(input).split('?');
    const path = rawPath;
    const method = init.method ?? 'GET';
    const headers = (init.headers ?? {}) as Record<string, string>;
    const correlationId = headers['X-Correlation-Id'] ?? null;

    requests.push({ path, method, correlationId });

    if (failing.includes(path)) {
      return problem(503, 'Service Unavailable', correlationId);
    }

    // --- Autenticación: la aporta la aplicación, no TEAF ---
    if (path === config.authEndpoints.login) {
      // El `HttpClient` siempre serializa el cuerpo a JSON antes de enviarlo.
      const raw = typeof init.body === 'string' ? init.body : '{}';
      const body = JSON.parse(raw) as Record<string, string>;
      const valid =
        body['username'] === VALID_CREDENTIALS.username &&
        body['password'] === VALID_CREDENTIALS.password;

      if (!valid) return problem(401, 'Credenciales incorrectas', correlationId);

      sessionOpen = true;
      return json({
        accessToken: ACCESS_TOKEN,
        refreshToken: REFRESH_TOKEN,
        tokenType: 'Bearer',
        expiresIn: 900,
      });
    }

    if (path === config.authEndpoints.logout) {
      sessionOpen = false;
      return new Response(null, { status: 204 });
    }

    if (path === config.authEndpoints.refresh) {
      if (!sessionOpen) return problem(401, 'Refresh token no válido', correlationId);
      return json({
        accessToken: ACCESS_TOKEN,
        refreshToken: REFRESH_TOKEN,
        tokenType: 'Bearer',
        expiresIn: 900,
      });
    }

    // Todo lo demás exige sesión, incluido el propio endpoint de identidad.
    const authorized = headers['Authorization'] === `Bearer ${ACCESS_TOKEN}` && sessionOpen;
    if (!authorized) return problem(401, 'No autenticado', correlationId);

    if (path === config.authEndpoints.me) return json(PRINCIPAL);

    // --- Endpoints reales de TEAF ---
    switch (path) {
      case '/health':
        return json(HEALTH);
      case '/runtime/info':
        return json(RUNTIME_INFO);
      case '/runtime/modules':
        return json(collection(RUNTIME_MODULES));
      case '/runtime/events': {
        const events = collection(RUNTIME_EVENTS);
        const limit = new URLSearchParams(queryString ?? '').get('limit');
        // El recorte lo hace el servidor, igual que el TEAF real.
        return json(limit === null ? events : events.slice(0, Number(limit)));
      }
      case '/runtime/services':
      case '/runtime/capabilities':
      case '/runtime/features':
      case '/runtime/plugins':
        // Vacías en un TEAF sin extensiones registradas.
        return json([]);
      default:
        return problem(404, 'Not Found', correlationId);
    }
  }

  return {
    fetch: (input, init = {}) => Promise.resolve(respond(input, init)),
    requests,
    hasSession: () => sessionOpen,
  };
}
