import { Box, Button, Paper, Typography } from '@mui/material';
import type { ReactElement } from 'react';
import { Link, useLocation } from 'react-router-dom';

/**
 * Ruta inexistente.
 *
 * Se muestra en lugar de redirigir en silencio a la portada: un enlace roto o
 * una URL mal escrita son cosas que el usuario necesita ver para corregirlas,
 * y una redirección callada las convierte en «la aplicación me ha llevado a
 * otro sitio sin explicación».
 */
export function NotFoundPage(): ReactElement {
  const location = useLocation();

  return (
    <Box sx={{ display: 'flex', justifyContent: 'center', pt: 4 }}>
      <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', maxWidth: 480 }}>
        <Typography variant="h5" component="h1" gutterBottom>
          Página no encontrada
        </Typography>
        <Typography variant="body2" color="text.secondary">
          La ruta <code>{location.pathname}</code> no existe en esta aplicación.
        </Typography>
        <Button component={Link} to="/" variant="contained" sx={{ mt: 3 }}>
          Volver al panel
        </Button>
      </Paper>
    </Box>
  );
}
