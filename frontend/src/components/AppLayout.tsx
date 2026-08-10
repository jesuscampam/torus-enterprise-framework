import { AppBar, Box, Button, Container, Toolbar, Typography } from '@mui/material';
import type { ReactElement } from 'react';
import { Outlet } from 'react-router-dom';

import { useAuth } from '@/hooks/useAuth';

/**
 * Marco visual común de la aplicación: barra superior y contenedor de la ruta activa.
 *
 * Deliberadamente escueto. La navegación lateral, las migas de pan y la barra de
 * estado son Sprint 3.5b (librería de componentes); aquí solo está lo que el
 * shell necesita para funcionar.
 */
export function AppLayout(): ReactElement {
  const { isAuthenticated, principal, logout } = useAuth();

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="h1" sx={{ flexGrow: 1 }}>
            TEAF
          </Typography>
          {isAuthenticated && (
            <>
              <Typography variant="body2" sx={{ mr: 2 }}>
                {principal?.identity.claims.name ?? principal?.identity.id}
              </Typography>
              <Button color="inherit" onClick={() => void logout()}>
                Cerrar sesión
              </Button>
            </>
          )}
        </Toolbar>
      </AppBar>

      <Container component="main" sx={{ flexGrow: 1, py: 4 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
