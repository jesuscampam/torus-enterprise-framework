import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { HEADER_CORRELATION_ID, HttpClient } from './client';
import { ApiError, NetworkError } from './errors';

/** Respuesta JSON mínima, como la que devolvería `fetch`. */
function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('HttpClient', () => {
  // Tipado como `fetch`: con `vi.fn()` a secas el retorno se infiere `void` y
  // devolver una promesa dispara `no-misused-promises`.
  let fetchMock: ReturnType<typeof vi.fn<typeof fetch>>;

  beforeEach(() => {
    fetchMock = vi.fn<typeof fetch>();
    vi.stubGlobal('fetch', fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function client(overrides: Partial<ConstructorParameters<typeof HttpClient>[0]> = {}) {
    return new HttpClient({
      baseUrl: '',
      requestTimeoutMs: 5_000,
      ...overrides,
    });
  }

  it('devuelve el cuerpo deserializado en una respuesta correcta', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ version: '0.11.0-alpha' }));

    const result = await client().get<{ version: string }>('/info');

    expect(result).toEqual({ version: '0.11.0-alpha' });
  });

  it('envía una cabecera de correlación distinta en cada petición', async () => {
    // Una respuesta nueva por llamada: el cuerpo de un `Response` solo se lee
    // una vez, y `mockResolvedValue` devolvería siempre la misma instancia.
    fetchMock.mockImplementation(() => Promise.resolve(jsonResponse({})));
    const api = client();

    await api.get('/info');
    await api.get('/info');

    const first = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const second = fetchMock.mock.calls[1]?.[1] as RequestInit;
    const firstId = (first.headers as Record<string, string>)[HEADER_CORRELATION_ID];
    const secondId = (second.headers as Record<string, string>)[HEADER_CORRELATION_ID];

    expect(firstId).toBeTruthy();
    expect(secondId).toBeTruthy();
    expect(firstId).not.toBe(secondId);
  });

  it('adjunta el access token como Bearer cuando hay sesión', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));

    await client({ getAccessToken: () => 'token-abc' }).get('/info');

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>)['Authorization']).toBe('Bearer token-abc');
  });

  it('omite Authorization cuando no hay sesión', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));

    await client({ getAccessToken: () => null }).get('/info');

    const init = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect((init.headers as Record<string, string>)['Authorization']).toBeUndefined();
  });

  it('traduce un Problem Details del backend a ApiError conservando el correlationId', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        {
          type: 'https://teaf.torus/errors/validation-error',
          title: 'Error de validación',
          status: 422,
          detail: "El campo 'priority' no es válido.",
          correlationId: 'corr-123',
        },
        422
      )
    );

    const error = await client()
      .post('/incidents', {})
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    const apiError = error as ApiError;
    expect(apiError.status).toBe(422);
    expect(apiError.isValidationError).toBe(true);
    expect(apiError.correlationId).toBe('corr-123');
    expect(apiError.message).toBe("El campo 'priority' no es válido.");
  });

  it('sintetiza un ApiError cuando el error no viene en formato Problem Details', async () => {
    fetchMock.mockResolvedValue(
      new Response('<html>502 Bad Gateway</html>', {
        status: 502,
        statusText: 'Bad Gateway',
      })
    );

    const error = (await client()
      .get('/info')
      .catch((caught: unknown) => caught)) as ApiError;

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(502);
    // Al no traerlo el intermediario, se conserva el generado por el cliente.
    expect(error.correlationId).toBeTruthy();
  });

  it('convierte un fallo de red en NetworkError', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    const error = await client()
      .get('/info')
      .catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(NetworkError);
  });

  it('devuelve undefined sin intentar parsear un 204 sin cuerpo', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    await expect(client().delete('/incidents/1')).resolves.toBeUndefined();
  });

  it('serializa los query params y omite los undefined', async () => {
    fetchMock.mockResolvedValue(jsonResponse({}));

    await client().get('/incidents', {
      query: { page: 2, status: 'open', sort: undefined },
    });

    const url = fetchMock.mock.calls[0]?.[0] as string;
    expect(url).toContain('page=2');
    expect(url).toContain('status=open');
    expect(url).not.toContain('sort');
  });

  describe('renovación de sesión ante un 401', () => {
    it('renueva y reintenta la petición original con el token nuevo', async () => {
      fetchMock
        .mockResolvedValueOnce(new Response(null, { status: 401 }))
        .mockResolvedValueOnce(jsonResponse({ ok: true }));
      const refreshAccessToken = vi.fn().mockResolvedValue('token-nuevo');

      const result = await client({
        refreshAccessToken,
        getAccessToken: () => 'token-viejo',
      }).get<{
        ok: boolean;
      }>('/protegido');

      expect(result).toEqual({ ok: true });
      expect(refreshAccessToken).toHaveBeenCalledTimes(1);
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it('no reintenta indefinidamente si tras renovar sigue devolviendo 401', async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 401 }));
      const refreshAccessToken = vi.fn().mockResolvedValue('token-nuevo');

      const error = await client({ refreshAccessToken })
        .get('/protegido')
        .catch((caught: unknown) => caught);

      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).isUnauthorized).toBe(true);
      expect(refreshAccessToken).toHaveBeenCalledTimes(1);
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });

    it('renueva una sola vez aunque varias peticiones reciban 401 a la vez', async () => {
      // Las tres primeras llamadas dan 401; el resto (los reintentos) van bien.
      let call = 0;
      fetchMock.mockImplementation(() => {
        call += 1;
        return Promise.resolve(call <= 3 ? new Response(null, { status: 401 }) : jsonResponse({}));
      });
      const refreshAccessToken = vi.fn().mockResolvedValue('token-nuevo');
      const api = client({ refreshAccessToken });

      await Promise.all([api.get('/a'), api.get('/b'), api.get('/c')]);

      // Sin single-flight serían tres refrescos, y con rotación de refresh
      // tokens en el backend dos de ellos fallarían.
      expect(refreshAccessToken).toHaveBeenCalledTimes(1);
    });

    it('propaga el 401 sin renovar cuando no hay manejador de refresco', async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 401 }));

      const error = await client()
        .get('/protegido')
        .catch((caught: unknown) => caught);

      expect(error).toBeInstanceOf(ApiError);
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it('no intenta renovar cuando el llamante lo desactiva', async () => {
      fetchMock.mockResolvedValue(new Response(null, { status: 401 }));
      const refreshAccessToken = vi.fn().mockResolvedValue('token-nuevo');

      const error = await client({ refreshAccessToken })
        .post('/auth/refresh', {}, { retryOnUnauthorized: false })
        .catch((caught: unknown) => caught);

      expect(error).toBeInstanceOf(ApiError);
      expect(refreshAccessToken).not.toHaveBeenCalled();
    });

    it('no se queda colgado cuando la propia renovación recibe un 401', async () => {
      // Regresión (Sprint 3.5c): con el refresh token caducado, la petición de
      // renovación devolvía 401, pedía otra renovación y `refreshOnce` le
      // entregaba la promesa en curso —la que esperaba a esa misma petición—.
      // Las dos se esperaban entre sí y la sesión no se cerraba nunca: la
      // aplicación se quedaba fija en «Verificando sesión».
      fetchMock.mockResolvedValue(new Response(null, { status: 401 }));
      const api = client({
        // Reproduce al manejador real del store: renueva usando el mismo cliente.
        refreshAccessToken: async () => {
          try {
            await api.post('/auth/refresh', {}, { retryOnUnauthorized: false });
            return 'token-nuevo';
          } catch {
            return null;
          }
        },
      });

      const error = await api.get('/me').catch((caught: unknown) => caught);

      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(401);
    });
  });
});
