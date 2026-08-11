import { Box, Drawer, List, ListItem, ListItemButton, ListItemText, Toolbar } from '@mui/material';
import type { ReactElement } from 'react';
import { NavLink } from 'react-router-dom';

import { navigationItems } from './navigationItems';

/** Ancho del cajón lateral; compartido con `AppLayout` para reservar el hueco. */
export const NAVIGATION_WIDTH = 220;

interface AppNavigationProps {
  /** Cajón temporal abierto (solo móvil). */
  open: boolean;
  onClose: () => void;
}

function NavigationList({ onNavigate }: { onNavigate?: () => void }): ReactElement {
  return (
    <List component="nav" aria-label="Navegación principal">
      {navigationItems.map((item) => (
        <ListItem key={item.path} disablePadding>
          <ListItemButton
            component={NavLink}
            to={item.path}
            // `end` limita la coincidencia exacta a la raíz: sin esto, "/" se
            // marcaría como activa estando en cualquier otra ruta.
            end={item.path === '/'}
            onClick={onNavigate}
            sx={{
              '&.active': {
                backgroundColor: 'action.selected',
                fontWeight: 'fontWeightMedium',
              },
            }}
          >
            <ListItemText primary={item.label} secondary={item.description} />
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  );
}

/**
 * Navegación principal de la aplicación.
 *
 * Dos cajones, no uno con estilos condicionales: el permanente se monta solo en
 * escritorio y el temporal solo en móvil. Un único `Drawer` que cambie de
 * `variant` según el tamaño desmonta y remonta su contenido en cada cambio de
 * breakpoint, perdiendo el foco del teclado por el camino.
 */
export function AppNavigation({ open, onClose }: AppNavigationProps): ReactElement {
  return (
    <Box component="aside" sx={{ width: { md: NAVIGATION_WIDTH }, flexShrink: { md: 0 } }}>
      <Drawer
        variant="temporary"
        open={open}
        onClose={onClose}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: 'block', md: 'none' },
          '& .MuiDrawer-paper': { width: NAVIGATION_WIDTH, boxSizing: 'border-box' },
        }}
      >
        <NavigationList onNavigate={onClose} />
      </Drawer>

      <Drawer
        variant="permanent"
        open
        sx={{
          display: { xs: 'none', md: 'block' },
          '& .MuiDrawer-paper': { width: NAVIGATION_WIDTH, boxSizing: 'border-box' },
        }}
      >
        {/* Empuja la lista por debajo de la AppBar fija. */}
        <Toolbar />
        <NavigationList />
      </Drawer>
    </Box>
  );
}
