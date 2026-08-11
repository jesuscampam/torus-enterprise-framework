import { Alert, AlertTitle, Box, Button } from '@mui/material';
import type { ReactElement } from 'react';
import { Link } from 'react-router-dom';

/**
 * Destino cuando hay sesión válida pero faltan rol o permiso (HTTP 403).
 *
 * No dice **qué** rol o permiso falta: enumerar los que existen le da a un
 * usuario sin autorización un mapa de lo que hay detrás
 * (ver SECURITY-STANDARD.md). Con la vía de vuelta basta.
 */
export function ForbiddenPage(): ReactElement {
  return (
    <Box sx={{ pt: 4 }}>
      <Alert severity="error">
        <AlertTitle>Acceso denegado</AlertTitle>
        Tu cuenta no tiene los permisos necesarios para ver esta página.
      </Alert>
      <Button component={Link} to="/" variant="outlined" sx={{ mt: 3 }}>
        Volver al panel
      </Button>
    </Box>
  );
}
