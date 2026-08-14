import { Box, Container, Toolbar } from '@mui/material';
import { useState, type ReactElement } from 'react';
import { Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { AppNavigation, NAVIGATION_WIDTH } from './AppNavigation';

/**
 * Marco de la aplicación autenticada: cabecera, navegación y contenido.
 *
 * Solo envuelve las rutas privadas. El login y los destinos de error se montan
 * fuera, porque una barra con el botón «Cerrar sesión» sobre la pantalla de
 * inicio de sesión no describe ningún estado posible de la aplicación.
 *
 * El estado del cajón vive aquí y no en `AppHeader` porque lo comparten dos
 * componentes hermanos: quien abre es la cabecera y quien se abre es la
 * navegación. Subirlo al ancestro común es lo que evita duplicarlo.
 */
export function AppLayout(): ReactElement {
  const [navigationOpen, setNavigationOpen] = useState(false);

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppHeader onOpenNavigation={() => setNavigationOpen(true)} />
      <AppNavigation open={navigationOpen} onClose={() => setNavigationOpen(false)} />

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          width: { md: `calc(100% - ${NAVIGATION_WIDTH}px)` },
          minWidth: 0,
        }}
      >
        {/* Compensa la altura de la AppBar fija. */}
        <Toolbar />
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
}
