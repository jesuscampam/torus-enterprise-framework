import { Alert, AlertTitle, Box } from '@mui/material';
import type { ReactElement } from 'react';

/** Destino cuando hay sesión válida pero faltan rol o permiso (HTTP 403). */
export function ForbiddenPage(): ReactElement {
  return (
    <Box sx={{ pt: 4 }}>
      <Alert severity="error">
        <AlertTitle>Acceso denegado</AlertTitle>
        Tu cuenta no tiene los permisos necesarios para ver esta página.
      </Alert>
    </Box>
  );
}
