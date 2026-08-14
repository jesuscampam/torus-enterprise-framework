import { Alert, AlertTitle, Box, Button, Typography } from '@mui/material';
import type { ReactElement } from 'react';

import { ApiError, NetworkError } from '@/services';

interface ErrorStateProps {
  /** El error tal cual lo entregó la consulta. Nunca se muestra en crudo. */
  error: unknown;
  /** Si se indica, se ofrece un botón de reintento. */
  onRetry?: () => void;
  /** Encabezado; por defecto, uno genérico de carga. */
  title?: string;
}

/**
 * Mensaje amigable derivado del error, **sin filtrar detalles internos**.
 *
 * Un 500 puede traer en `detail` información del servidor que no le corresponde
 * ver al usuario, así que los errores de servidor se resumen en un texto fijo.
 * Los 4xx sí se explican: son accionables por quien está delante.
 */
function friendlyMessage(error: unknown): string {
  if (error instanceof NetworkError) {
    return 'No se pudo contactar con el servidor. Comprueba tu conexión e inténtalo de nuevo.';
  }

  if (error instanceof ApiError) {
    if (error.status === 401) return 'Tu sesión ha caducado. Vuelve a iniciar sesión.';
    if (error.status === 403) return 'No tienes permisos para consultar esta información.';
    if (error.status === 404) return 'La información solicitada no existe o ya no está disponible.';
    if (error.status >= 500) {
      return 'El servidor no pudo completar la petición. Inténtalo de nuevo en unos instantes.';
    }
    return error.problem.detail ?? error.problem.title;
  }

  return 'No fue posible cargar la información.';
}

/**
 * Fallo al obtener datos.
 *
 * Muestra qué pasó en términos del usuario y, cuando el backend lo aportó, el
 * `correlationId`: es la pieza que permite a soporte encontrar la traza exacta
 * en los logs del servidor sin pedirle al usuario que reproduzca el problema
 * (ver LOGGING-STANDARD.md). No se vuelca nunca el error en crudo.
 */
export function ErrorState({
  error,
  onRetry,
  title = 'No fue posible cargar la información',
}: ErrorStateProps): ReactElement {
  const correlationId = error instanceof ApiError ? error.correlationId : undefined;

  return (
    <Alert
      severity="error"
      action={
        onRetry && (
          <Button color="inherit" size="small" onClick={onRetry}>
            Reintentar
          </Button>
        )
      }
    >
      <AlertTitle>{title}</AlertTitle>
      <Typography variant="body2">{friendlyMessage(error)}</Typography>
      {correlationId && (
        <Box sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Referencia para soporte: {correlationId}
          </Typography>
        </Box>
      )}
    </Alert>
  );
}
