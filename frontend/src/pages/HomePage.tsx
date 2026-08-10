import { Alert, Box, Card, CardContent, CircularProgress, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import type { ReactElement } from 'react';

import { useAuth } from '@/hooks/useAuth';
import { httpClient } from '@/services';

interface FrameworkInfo {
  name?: string;
  version?: string;
  environment?: string;
}

/**
 * Pantalla de inicio.
 *
 * Sirve además de referencia viva de la separación que fija ADR-013 §3: el
 * `Principal` sale del store (estado de cliente) y la información del framework
 * sale de TanStack Query (estado de servidor, con su caché y sus estados de
 * carga y error). No se mezclan.
 */
export function HomePage(): ReactElement {
  const { principal } = useAuth();

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['framework', 'info'],
    queryFn: ({ signal }) => httpClient.get<FrameworkInfo>('/info', { signal }),
  });

  return (
    <Box>
      <Typography variant="h4" component="h2" gutterBottom>
        Bienvenido
        {principal?.identity.claims.name ? `, ${principal.identity.claims.name}` : ''}
      </Typography>

      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Typography variant="h6" component="h3" gutterBottom>
            Backend
          </Typography>

          {isPending && <CircularProgress size={24} aria-label="Cargando información" />}

          {isError && (
            <Alert severity="warning">
              No se pudo obtener la información del backend: {error.message}
            </Alert>
          )}

          {data && (
            <Typography variant="body2">
              {data.name ?? 'TEAF'} · versión {data.version ?? 'desconocida'} · entorno{' '}
              {data.environment ?? 'desconocido'}
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
