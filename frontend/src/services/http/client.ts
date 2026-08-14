import type { HttpMethod } from '@/types/api';

import { ApiError, NetworkError, toProblemDetails } from './errors';

/** Cabecera de correlación — misma constante que `HEADER_CORRELATION_ID` en backend. */
export const HEADER_CORRELATION_ID = 'X-Correlation-Id';

export interface HttpClientOptions {
  /** Base de la URL. Vacío = mismo origen. */
  baseUrl: string;
  requestTimeoutMs: number;
  /**
   * Devuelve el access token vigente, o `null` si no hay sesión.
   *
   * Es una función y no un valor para que el cliente no dependa del store: la
   * dirección de la dependencia apunta hacia adentro, igual que en backend
   * (ARCHITECTURE.md). El store conoce al cliente; el cliente no conoce al store.
   */
  getAccessToken?: () => string | null;
  /**
   * Intenta renovar la sesión tras un 401 y devuelve el nuevo access token, o
   * `null` si la renovación no es posible. Si se omite, un 401 se propaga tal cual.
   */
  refreshAccessToken?: () => Promise<string | null>;
}

export interface RequestOptions {
  /** Query params; los `undefined` se omiten. */
  query?: Record<string, string | number | boolean | undefined>;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  /**
   * Si un 401 debe intentar renovar la sesión y reintentar. `true` por defecto.
   *
   * **La propia petición de renovación tiene que desactivarlo.** Si no, su 401
   * vuelve a pedir una renovación, `refreshOnce` le devuelve la promesa que
   * todavía está en curso —la que espera precisamente a esa petición— y las dos
   * se quedan esperándose: la sesión nunca se cierra y la pantalla se queda
   * colgada en «Verificando sesión».
   */
  retryOnUnauthorized?: boolean;
}

interface SendOptions extends RequestOptions {
  method: HttpMethod;
  path: string;
  body?: unknown;
  /** Interno: evita que un reintento tras refrescar vuelva a reintentar. */
  isRetry?: boolean;
}

function newCorrelationId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  // Entornos sin Web Crypto (jsdom antiguo, navegadores en contexto inseguro).
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}

function buildUrl(baseUrl: string, path: string, query: RequestOptions['query']): string {
  const url = `${baseUrl}${path}`;
  if (!query) return url;

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) params.append(key, String(value));
  }
  const queryString = params.toString();
  return queryString ? `${url}?${queryString}` : url;
}

/**
 * Cliente HTTP tipado hacia el backend TEAF.
 *
 * Concentra en un solo sitio las cuatro cosas que si no acaban copiadas en cada
 * llamada: la cabecera de correlación, el `Authorization`, la traducción de
 * errores a `ApiError` y el timeout.
 *
 * **Renovación de sesión**: ante un 401 llama a `refreshAccessToken` una sola
 * vez aunque haya varias peticiones fallando a la vez (*single-flight*) y
 * reintenta la original. Sin eso, cargar una pantalla con cuatro peticiones en
 * paralelo produce cuatro refrescos simultáneos y, con rotación de refresh
 * tokens en el backend, tres de ellos fallan.
 */
export class HttpClient {
  private readonly options: HttpClientOptions;
  private refreshInFlight: Promise<string | null> | null = null;

  constructor(options: HttpClientOptions) {
    this.options = options;
  }

  get<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.send<T>({ ...options, method: 'GET', path });
  }

  post<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.send<T>({ ...options, method: 'POST', path, body });
  }

  put<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.send<T>({ ...options, method: 'PUT', path, body });
  }

  patch<T>(path: string, body?: unknown, options: RequestOptions = {}): Promise<T> {
    return this.send<T>({ ...options, method: 'PATCH', path, body });
  }

  delete<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.send<T>({ ...options, method: 'DELETE', path });
  }

  private async send<T>(options: SendOptions): Promise<T> {
    const {
      method,
      path,
      body,
      query,
      signal,
      headers = {},
      isRetry = false,
      retryOnUnauthorized = true,
    } = options;
    const correlationId = newCorrelationId();

    const requestHeaders: Record<string, string> = {
      Accept: 'application/json',
      [HEADER_CORRELATION_ID]: correlationId,
      ...headers,
    };

    if (body !== undefined) requestHeaders['Content-Type'] = 'application/json';

    const token = this.options.getAccessToken?.();
    if (token) requestHeaders['Authorization'] = `Bearer ${token}`;

    const timeout = AbortSignal.timeout(this.options.requestTimeoutMs);
    // El signal del llamante (p. ej. el de TanStack Query al cancelar) y el del
    // timeout deben poder abortar ambos.
    const combinedSignal = signal ? AbortSignal.any([signal, timeout]) : timeout;

    let response: Response;
    try {
      response = await fetch(buildUrl(this.options.baseUrl, path, query), {
        method,
        headers: requestHeaders,
        body: body === undefined ? null : JSON.stringify(body),
        signal: combinedSignal,
      });
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'TimeoutError') {
        throw new NetworkError(
          `La petición ${method} ${path} superó ${this.options.requestTimeoutMs} ms`,
          cause
        );
      }
      // Una cancelación deliberada del llamante se propaga sin disfrazarla de
      // error de red: quien canceló ya sabe por qué.
      if (cause instanceof DOMException && cause.name === 'AbortError') throw cause;
      throw new NetworkError(`No se pudo contactar con la API (${method} ${path})`, cause);
    }

    if (
      response.status === 401 &&
      !isRetry &&
      retryOnUnauthorized &&
      this.options.refreshAccessToken
    ) {
      const refreshed = await this.refreshOnce();
      if (refreshed) return this.send<T>({ ...options, isRetry: true });
    }

    if (!response.ok) {
      throw new ApiError(await toProblemDetails(response, correlationId));
    }

    // 204 No Content y 205 Reset Content no traen cuerpo — API-STANDARD.md §7.
    if (response.status === 204 || response.status === 205) return undefined as T;

    return (await response.json()) as T;
  }

  /** Renueva la sesión compartiendo una única promesa entre llamantes concurrentes. */
  private refreshOnce(): Promise<string | null> {
    this.refreshInFlight ??= (this.options.refreshAccessToken?.() ?? Promise.resolve(null))
      .catch(() => null)
      .finally(() => {
        this.refreshInFlight = null;
      });
    return this.refreshInFlight;
  }
}
