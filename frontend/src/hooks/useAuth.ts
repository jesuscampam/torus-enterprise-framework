import { useAuthStore } from '@/store/authStore';

/**
 * Acceso a la sesión desde un componente.
 *
 * Fachada sobre el store para que los componentes no dependan de la forma
 * interna del estado: si mañana cambia, cambia aquí y no en cada pantalla.
 */
export function useAuth() {
  const status = useAuthStore((state) => state.status);
  const principal = useAuthStore((state) => state.principal);
  const error = useAuthStore((state) => state.error);
  const login = useAuthStore((state) => state.login);
  const logout = useAuthStore((state) => state.logout);
  const hasRole = useAuthStore((state) => state.hasRole);
  const hasPermission = useAuthStore((state) => state.hasPermission);

  return {
    status,
    principal,
    error,
    login,
    logout,
    hasRole,
    hasPermission,
    isAuthenticated: status === 'authenticated',
    isAuthenticating: status === 'authenticating',
  };
}
