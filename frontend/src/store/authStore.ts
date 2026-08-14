import { create } from 'zustand';

import { ApiError, authService, sessionBridge, tokenStorage } from '@/services';
import type { AuthStatus, Credentials, Principal, TokenPair } from '@/types/auth';

/**
 * Estado **de cliente** de la sesión (ADR-013 §3).
 *
 * Aquí vive solo lo que es del navegador: qué tokens tenemos y quién es el
 * usuario en curso. Los datos de negocio que se leen del backend NO van en este
 * store — van en TanStack Query, que sabe cachearlos, revalidarlos e
 * invalidarlos. Mezclarlos es el antipatrón que ADR-013 §3 describe.
 */
interface AuthState {
  status: AuthStatus;
  principal: Principal | null;
  tokens: TokenPair | null;
  /** Mensaje del último fallo de login, listo para mostrar. */
  error: string | null;

  login: (credentials: Credentials) => Promise<void>;
  logout: () => Promise<void>;
  /** Recupera la sesión persistida al arrancar la aplicación. */
  restore: () => Promise<void>;
  hasRole: (role: string) => boolean;
  hasPermission: (permission: string) => boolean;
}

export const useAuthStore = create<AuthState>((set, get) => {
  /** Publica los tokens en las tres partes que deben verlos, o los borra en todas. */
  function commitTokens(tokens: TokenPair | null): void {
    if (tokens) {
      tokenStorage.write(tokens);
      sessionBridge.setAccessToken(tokens.accessToken);
    } else {
      tokenStorage.clear();
      sessionBridge.setAccessToken(null);
    }
    set({ tokens });
  }

  function clearSession(): void {
    commitTokens(null);
    set({ status: 'anonymous', principal: null });
  }

  return {
    status: 'anonymous',
    principal: null,
    tokens: null,
    error: null,

    async login(credentials: Credentials): Promise<void> {
      set({ status: 'authenticating', error: null });
      try {
        const tokens = await authService.login(credentials);
        commitTokens(tokens);

        const principal = await authService.currentPrincipal();
        set({ status: 'authenticated', principal });
      } catch (error) {
        clearSession();
        set({
          error:
            error instanceof ApiError
              ? error.message
              : 'No se pudo iniciar sesión. Inténtalo de nuevo.',
        });
        throw error;
      }
    },

    async logout(): Promise<void> {
      await authService.logout();
      clearSession();
    },

    async restore(): Promise<void> {
      const stored = tokenStorage.read();
      if (!stored) return;

      commitTokens(stored);
      set({ status: 'authenticating' });
      try {
        const principal = await authService.currentPrincipal();
        set({ status: 'authenticated', principal });
      } catch {
        // Tokens caducados o revocados entre sesiones: equivale a no tener sesión.
        clearSession();
      }
    },

    hasRole(role: string): boolean {
      return get().principal?.roles.includes(role) ?? false;
    },

    hasPermission(permission: string): boolean {
      return get().principal?.permissions.includes(permission) ?? false;
    },
  };
});

/**
 * Enseña al `HttpClient` a renovar la sesión ante un 401.
 *
 * El cliente aplica *single-flight* sobre esta función, así que aquí no hace
 * falta preocuparse por llamadas concurrentes. Si la renovación falla, se cierra
 * la sesión: el refresh token ya no vale y seguir intentándolo solo produce más
 * 401 en cadena.
 */
sessionBridge.setRefreshHandler(async () => {
  const current = useAuthStore.getState().tokens;
  if (!current) return null;

  try {
    const renewed = await authService.refresh(current.refreshToken);
    tokenStorage.write(renewed);
    sessionBridge.setAccessToken(renewed.accessToken);
    useAuthStore.setState({ tokens: renewed });
    return renewed.accessToken;
  } catch {
    tokenStorage.clear();
    sessionBridge.setAccessToken(null);
    useAuthStore.setState({
      status: 'anonymous',
      principal: null,
      tokens: null,
    });
    return null;
  }
});
