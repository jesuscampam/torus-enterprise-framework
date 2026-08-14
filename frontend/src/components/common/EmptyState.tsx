import { Box, Button, Paper, Typography } from '@mui/material';
import type { ReactElement, ReactNode } from 'react';

interface EmptyStateProps {
  /** Qué falta, en positivo. Por ejemplo: «No hay eventos registrados». */
  title: string;
  /** Por qué está vacío o qué haría que dejara de estarlo. */
  description?: string;
  /** Acción principal, cuando el usuario puede hacer algo al respecto. */
  action?: ReactNode;
}

/**
 * Ausencia de datos.
 *
 * Es un estado distinto del error y merece un tratamiento distinto: una tabla
 * vacía porque todavía no hay nada que mostrar no es un fallo, y presentarla
 * como tal enseña al usuario a desconfiar de mensajes que sí importan.
 */
export function EmptyState({ title, description, action }: EmptyStateProps): ReactElement {
  return (
    <Paper variant="outlined" sx={{ p: 4, textAlign: 'center', backgroundColor: 'transparent' }}>
      <Typography variant="subtitle1" component="p" gutterBottom>
        {title}
      </Typography>
      {description && (
        <Typography variant="body2" color="text.secondary">
          {description}
        </Typography>
      )}
      {action && <Box sx={{ mt: 3 }}>{action}</Box>}
    </Paper>
  );
}

interface EmptyStateActionProps {
  label: string;
  onClick: () => void;
}

/** Botón de acción con el estilo que `EmptyState` espera. */
export function EmptyStateAction({ label, onClick }: EmptyStateActionProps): ReactElement {
  return (
    <Button variant="outlined" onClick={onClick}>
      {label}
    </Button>
  );
}
