import { Box, Container } from '@mui/material';
import type { ReactElement } from 'react';
import { Outlet } from 'react-router-dom';

/**
 * Marco de las rutas públicas (login, acceso denegado, ruta inexistente).
 *
 * Deliberadamente sin cabecera ni navegación: quien todavía no tiene sesión no
 * tiene a dónde navegar, y ofrecerle un menú que le va a rebotar al login es
 * peor que no ofrecerle ninguno.
 */
export function PublicLayout(): ReactElement {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <Container component="main" maxWidth="sm" sx={{ flexGrow: 1, py: 6 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
