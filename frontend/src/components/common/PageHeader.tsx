import { Box, Divider, Typography } from '@mui/material';
import type { ReactElement, ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  /** Qué es esta pantalla, en una línea. */
  description?: string;
  /** Acciones de la pantalla (recargar, crear, exportar…). */
  actions?: ReactNode;
}

/**
 * Encabezado de pantalla.
 *
 * Fija el nivel semántico del título (`h1`) en un solo sitio: repetido a mano en
 * cada página acaba produciendo jerarquías incoherentes, que es exactamente lo
 * que rompe la navegación por encabezados de un lector de pantalla.
 */
export function PageHeader({ title, description, actions }: PageHeaderProps): ReactElement {
  return (
    <Box sx={{ mb: 3 }}>
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
        }}
      >
        <Box>
          <Typography variant="h4" component="h1">
            {title}
          </Typography>
          {description && (
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              {description}
            </Typography>
          )}
        </Box>
        {actions && <Box sx={{ display: 'flex', gap: 1 }}>{actions}</Box>}
      </Box>
      <Divider sx={{ mt: 2 }} />
    </Box>
  );
}
