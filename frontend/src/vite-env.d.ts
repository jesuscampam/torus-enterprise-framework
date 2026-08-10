/// <reference types="vite/client" />

/**
 * Variables de entorno del frontend.
 *
 * Solo las de prefijo `VITE_` llegan al navegador, y **todas son públicas**:
 * quedan incrustadas en el bundle. Nunca un secreto aquí (SECURITY-STANDARD.md).
 */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_API_VERSION?: string;
  readonly VITE_AUTH_LOGIN_PATH?: string;
  readonly VITE_AUTH_REFRESH_PATH?: string;
  readonly VITE_AUTH_LOGOUT_PATH?: string;
  readonly VITE_AUTH_ME_PATH?: string;
  readonly VITE_REQUEST_TIMEOUT_MS?: string;
  readonly VITE_PERSIST_SESSION?: string;
  readonly VITE_ENVIRONMENT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
