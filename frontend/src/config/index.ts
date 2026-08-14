/**
 * Configuración por entorno del frontend.
 *
 * Equivalente cliente de la configuración que TEAF expone en `teaf.configuration`
 * y aplicación del principio *Configuration by Environment*
 * ([ADR-005](../../../docs/architecture/adr/ADR-005-cloud-ready.md)):
 * nada de lo que cambia entre desarrollo, staging y producción se escribe en el
 * código; se lee de variables de entorno con un valor por defecto seguro.
 *
 * Vite solo expone al navegador las variables con prefijo `VITE_`. Es una
 * salvaguarda, no un descuido: **cualquier valor que llegue aquí es público**
 * — queda incrustado en el bundle y es legible por quien abra las DevTools.
 * Nunca se pone aquí un secreto (ver SECURITY-STANDARD.md).
 */

/**
 * Rutas de autenticación de la aplicación anfitriona.
 *
 * TEAF **no expone endpoints de login** (ver ADR-013): el framework entrega
 * primitivas de seguridad, y cada aplicación define sus propias rutas. Por eso
 * el cliente de auth las recibe por configuración en vez de cablearlas.
 */
export interface AuthEndpoints {
  login: string;
  refresh: string;
  logout: string;
  /** Devuelve el `Principal` de la sesión en curso. */
  me: string;
}

export interface AppConfig {
  /** Base de toda llamada a la API. Vacío = mismo origen (el caso de producción). */
  apiBaseUrl: string;
  /** Prefijo de versión — API-STANDARD.md §2 exige `/api/v1` explícito. */
  apiVersion: string;
  authEndpoints: AuthEndpoints;
  /** Milisegundos antes de abortar una petición. */
  requestTimeoutMs: number;
  /**
   * Persistir tokens en `localStorage`. Por defecto `false`: los tokens viven
   * solo en memoria, que es lo resistente a XSS. Activarlo es una decisión
   * consciente de la aplicación (ADR-013 §5, SECURITY-STANDARD.md §2).
   */
  persistSession: boolean;
  environment: string;
}

/**
 * Vista tipada del entorno.
 *
 * Vite sustituye `import.meta.env.X` en tiempo de build, y su tipo indexado es
 * `any`. Acotarlo aquí una vez evita que ese `any` se propague por el módulo.
 */
const env: Record<string, string | undefined> = import.meta.env;

function readString(key: string, fallback: string): string {
  const value = env[key];
  return value !== undefined && value.length > 0 ? value : fallback;
}

function readBoolean(key: string, fallback: boolean): boolean {
  const value = env[key];
  if (value === undefined || value.length === 0) return fallback;
  return value === 'true' || value === '1';
}

function readNumber(key: string, fallback: number): number {
  const value = env[key];
  if (value === undefined || value.length === 0) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const apiVersion = readString('VITE_API_VERSION', '/api/v1');

export const config: AppConfig = {
  apiBaseUrl: readString('VITE_API_BASE_URL', ''),
  apiVersion,
  authEndpoints: {
    login: readString('VITE_AUTH_LOGIN_PATH', `${apiVersion}/auth/login`),
    refresh: readString('VITE_AUTH_REFRESH_PATH', `${apiVersion}/auth/refresh`),
    logout: readString('VITE_AUTH_LOGOUT_PATH', `${apiVersion}/auth/logout`),
    me: readString('VITE_AUTH_ME_PATH', `${apiVersion}/auth/me`),
  },
  requestTimeoutMs: readNumber('VITE_REQUEST_TIMEOUT_MS', 30_000),
  persistSession: readBoolean('VITE_PERSIST_SESSION', false),
  environment: readString('VITE_ENVIRONMENT', 'development'),
};
