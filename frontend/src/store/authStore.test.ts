import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services/http/errors';
import type { Principal, TokenPair } from '@/types/auth';

// Los dobles se declaran antes del `vi.mock` porque el hoisting lo sube al tope
// del módulo; usarlos directamente daría un error de acceso antes de inicializar.
const { authServiceMock, sessionBridgeMock, tokenStorageMock } = vi.hoisted(() => ({
  authServiceMock: {
    login: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    currentPrincipal: vi.fn(),
  },
  sessionBridgeMock: {
    setAccessToken: vi.fn(),
    setRefreshHandler: vi.fn(),
  },
  tokenStorageMock: {
    read: vi.fn(),
    write: vi.fn(),
    clear: vi.fn(),
    name: 'test',
  },
}));

vi.mock('@/services', async () => {
  const actual =
    await vi.importActual<typeof import('@/services/http/errors')>('@/services/http/errors');
  return {
    ApiError: actual.ApiError,
    NetworkError: actual.NetworkError,
    authService: authServiceMock,
    sessionBridge: sessionBridgeMock,
    tokenStorage: tokenStorageMock,
  };
});

const { useAuthStore } = await import('./authStore');

/**
 * El manejador de refresco que `authStore.ts` registró al importarse.
 *
 * Se captura aquí, en el momento del import, porque el `vi.clearAllMocks()` de
 * `beforeEach` borra el historial de llamadas y esa registración ocurre una sola
 * vez y no vuelve a repetirse.
 */
const registeredRefreshHandler = sessionBridgeMock.setRefreshHandler.mock
  .calls[0]?.[0] as () => Promise<string | null>;

const tokens: TokenPair = {
  accessToken: 'access-1',
  refreshToken: 'refresh-1',
  tokenType: 'Bearer',
  expiresIn: 900,
};

const principal: Principal = {
  identity: {
    id: 'u-1',
    providerId: 'jwt',
    claims: { subject: 'u-1', name: 'Ada' },
    authenticated: true,
  },
  roles: ['operator'],
  permissions: ['incidents:read'],
};

function unauthorized(): ApiError {
  return new ApiError({
    type: 'about:blank',
    title: 'No autorizado',
    status: 401,
    detail: 'Credenciales inválidas',
  });
}

describe('authStore', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      status: 'anonymous',
      principal: null,
      tokens: null,
      error: null,
    });
  });

  describe('login', () => {
    it('deja la sesión autenticada y publica el token en el puente', async () => {
      authServiceMock.login.mockResolvedValue(tokens);
      authServiceMock.currentPrincipal.mockResolvedValue(principal);

      await useAuthStore.getState().login({ username: 'ada', password: 'secreto' });

      const state = useAuthStore.getState();
      expect(state.status).toBe('authenticated');
      expect(state.principal).toEqual(principal);
      expect(state.tokens).toEqual(tokens);
      expect(sessionBridgeMock.setAccessToken).toHaveBeenCalledWith('access-1');
      expect(tokenStorageMock.write).toHaveBeenCalledWith(tokens);
    });

    it('ante credenciales inválidas limpia la sesión y expone el mensaje', async () => {
      authServiceMock.login.mockRejectedValue(unauthorized());

      await expect(
        useAuthStore.getState().login({ username: 'ada', password: 'mal' })
      ).rejects.toBeInstanceOf(ApiError);

      const state = useAuthStore.getState();
      expect(state.status).toBe('anonymous');
      expect(state.tokens).toBeNull();
      expect(state.error).toBe('Credenciales inválidas');
      expect(tokenStorageMock.clear).toHaveBeenCalled();
      expect(sessionBridgeMock.setAccessToken).toHaveBeenLastCalledWith(null);
    });

    it('no deja sesión a medias si el login va bien pero el principal falla', async () => {
      authServiceMock.login.mockResolvedValue(tokens);
      authServiceMock.currentPrincipal.mockRejectedValue(unauthorized());

      await expect(
        useAuthStore.getState().login({ username: 'ada', password: 'secreto' })
      ).rejects.toBeInstanceOf(ApiError);

      // Con tokens pero sin principal la app no sabría qué puede hacer el
      // usuario: es preferible quedar anónimo que autenticado a medias.
      expect(useAuthStore.getState().status).toBe('anonymous');
      expect(useAuthStore.getState().tokens).toBeNull();
    });
  });

  describe('logout', () => {
    it('limpia sesión, almacenamiento y puente', async () => {
      authServiceMock.logout.mockResolvedValue(undefined);
      useAuthStore.setState({ status: 'authenticated', principal, tokens });

      await useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.status).toBe('anonymous');
      expect(state.principal).toBeNull();
      expect(state.tokens).toBeNull();
      expect(tokenStorageMock.clear).toHaveBeenCalled();
      expect(sessionBridgeMock.setAccessToken).toHaveBeenLastCalledWith(null);
    });
  });

  describe('restore', () => {
    it('no hace nada si no hay tokens persistidos', async () => {
      tokenStorageMock.read.mockReturnValue(null);

      await useAuthStore.getState().restore();

      expect(useAuthStore.getState().status).toBe('anonymous');
      expect(authServiceMock.currentPrincipal).not.toHaveBeenCalled();
    });

    it('rehidrata la sesión cuando los tokens persistidos siguen siendo válidos', async () => {
      tokenStorageMock.read.mockReturnValue(tokens);
      authServiceMock.currentPrincipal.mockResolvedValue(principal);

      await useAuthStore.getState().restore();

      expect(useAuthStore.getState().status).toBe('authenticated');
      expect(useAuthStore.getState().principal).toEqual(principal);
    });

    it('limpia la sesión si los tokens persistidos ya caducaron', async () => {
      tokenStorageMock.read.mockReturnValue(tokens);
      authServiceMock.currentPrincipal.mockRejectedValue(unauthorized());

      await useAuthStore.getState().restore();

      expect(useAuthStore.getState().status).toBe('anonymous');
      expect(tokenStorageMock.clear).toHaveBeenCalled();
    });
  });

  describe('hasRole / hasPermission', () => {
    it('son falsos sin sesión', () => {
      expect(useAuthStore.getState().hasRole('operator')).toBe(false);
      expect(useAuthStore.getState().hasPermission('incidents:read')).toBe(false);
    });

    it('reflejan los roles y permisos del principal', () => {
      useAuthStore.setState({ status: 'authenticated', principal, tokens });

      expect(useAuthStore.getState().hasRole('operator')).toBe(true);
      expect(useAuthStore.getState().hasRole('admin')).toBe(false);
      expect(useAuthStore.getState().hasPermission('incidents:read')).toBe(true);
      expect(useAuthStore.getState().hasPermission('incidents:delete')).toBe(false);
    });
  });

  describe('manejador de refresco registrado en el puente', () => {
    it('devuelve el token nuevo y actualiza el estado', async () => {
      useAuthStore.setState({ status: 'authenticated', principal, tokens });
      const renewed: TokenPair = {
        ...tokens,
        accessToken: 'access-2',
        refreshToken: 'refresh-2',
      };
      authServiceMock.refresh.mockResolvedValue(renewed);

      await expect(registeredRefreshHandler()).resolves.toBe('access-2');

      expect(authServiceMock.refresh).toHaveBeenCalledWith('refresh-1');
      expect(useAuthStore.getState().tokens).toEqual(renewed);
    });

    it('cierra la sesión si el refresh token ya no vale', async () => {
      useAuthStore.setState({ status: 'authenticated', principal, tokens });
      authServiceMock.refresh.mockRejectedValue(unauthorized());

      await expect(registeredRefreshHandler()).resolves.toBeNull();

      expect(useAuthStore.getState().status).toBe('anonymous');
      expect(useAuthStore.getState().tokens).toBeNull();
    });

    it('devuelve null sin llamar al backend si no hay sesión', async () => {
      useAuthStore.setState({
        status: 'anonymous',
        principal: null,
        tokens: null,
      });

      await expect(registeredRefreshHandler()).resolves.toBeNull();
      expect(authServiceMock.refresh).not.toHaveBeenCalled();
    });
  });
});
