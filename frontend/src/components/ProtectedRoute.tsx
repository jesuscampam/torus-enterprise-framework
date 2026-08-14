import { Box, CircularProgress } from '@mui/material';
import type { ReactElement } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import { useAuth } from '@/hooks/useAuth';

interface ProtectedRouteProps {
  children: ReactElement;
  /** Si se indica, además de sesión se exige este rol. */
  requiredRole?: string;
  /** Si se indica, además de sesión se exige este permiso. */
  requiredPermission?: string;
}

/**
 * Puerta de acceso a una ruta.
 *
 * Complemento **de interfaz** a la autorización del backend, nunca su
 * sustituto: esconder un enlace no protege un endpoint. La comprobación que
 * manda es la de `SecurityMiddleware` + RBAC en servidor (ADR-007); esto solo
 * evita enseñar al usuario pantallas que el backend le va a denegar.
 */
export function ProtectedRoute({
  children,
  requiredRole,
  requiredPermission,
}: ProtectedRouteProps): ReactElement {
  const { isAuthenticated, isAuthenticating, hasRole, hasPermission } = useAuth();
  const location = useLocation();

  // Mientras se restaura la sesión no se puede decidir: redirigir aquí echaría
  // fuera a un usuario con sesión válida solo por llegar antes que la respuesta.
  if (isAuthenticating) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress aria-label="Verificando sesión" />
      </Box>
    );
  }

  if (!isAuthenticated) {
    // `state.from` permite volver a donde el usuario quería ir tras el login.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (requiredRole && !hasRole(requiredRole)) return <Navigate to="/forbidden" replace />;
  if (requiredPermission && !hasPermission(requiredPermission)) {
    return <Navigate to="/forbidden" replace />;
  }

  return children;
}
