/**
 * Composición de los servicios de la aplicación.
 *
 * Único lugar donde se instancian el cliente HTTP, el puente de sesión y el
 * servicio de autenticación — equivalente cliente del contenedor de
 * dependencias del backend. El resto de la aplicación importa de aquí y nunca
 * construye un `HttpClient` propio.
 */
import { config } from '@/config';

import { AuthService } from './auth/authService';
import {
  LocalStorageTokenStorage,
  MemoryTokenStorage,
  type TokenStorage,
} from './auth/tokenStorage';
import { HttpClient } from './http/client';
import { SessionBridge } from './http/session';

export const sessionBridge = new SessionBridge();

export const httpClient = new HttpClient({
  baseUrl: config.apiBaseUrl,
  requestTimeoutMs: config.requestTimeoutMs,
  getAccessToken: sessionBridge.getAccessToken,
  refreshAccessToken: sessionBridge.refreshAccessToken,
});

export const authService = new AuthService(httpClient, config.authEndpoints);

/**
 * Almacenamiento de tokens elegido por configuración.
 *
 * Memoria por defecto; `localStorage` solo si la aplicación activó
 * `VITE_PERSIST_SESSION` de forma explícita (ADR-013 §5).
 */
export const tokenStorage: TokenStorage = config.persistSession
  ? new LocalStorageTokenStorage()
  : new MemoryTokenStorage();

export { ApiError, NetworkError } from './http/errors';
export { HttpClient } from './http/client';
export { AuthService } from './auth/authService';
export {
  LocalStorageTokenStorage,
  MemoryTokenStorage,
  type TokenStorage,
} from './auth/tokenStorage';
