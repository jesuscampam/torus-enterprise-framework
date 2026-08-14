import { Box, CircularProgress, Typography } from '@mui/material';
import type { ReactElement } from 'react';

interface LoadingStateProps {
  /** Texto anunciado a lectores de pantalla y mostrado bajo el indicador. */
  label?: string;
}

/**
 * Indicador de carga uniforme.
 *
 * Existe para que "cargando" se vea y se anuncie igual en toda la aplicación.
 * El `role="status"` es lo que hace que un lector de pantalla anuncie el cambio
 * sin que el usuario tenga que ir a buscarlo.
 */
export function LoadingState({ label = 'Cargando…' }: LoadingStateProps): ReactElement {
  return (
    <Box
      role="status"
      aria-live="polite"
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 2,
        py: 6,
      }}
    >
      <CircularProgress aria-hidden />
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
    </Box>
  );
}
