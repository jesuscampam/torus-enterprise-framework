import { AppBar, Box, Button, IconButton, Toolbar, Typography } from '@mui/material';
import type { ReactElement } from 'react';

import { useAuth } from '@/hooks/useAuth';

interface AppHeaderProps {
  /** Abre el cajón de navegación en móvil. */
  onOpenNavigation: () => void;
}

/**
 * Icono de menú en SVG inline.
 *
 * `@mui/icons-material` no está en las dependencias del proyecto y traerlo
 * entero por un único glifo no se sostiene (STACK.md: ninguna dependencia nueva
 * sin ADR). `aria-hidden` porque quien nombra el botón es su `aria-label`.
 */
function MenuIcon(): ReactElement {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M3 6h18v2H3V6zm0 5h18v2H3v-2zm0 5h18v2H3v-2z" />
    </svg>
  );
}

/**
 * Barra superior: identidad de la aplicación, usuario y cierre de sesión.
 *
 * El nombre mostrado sale del `Principal` que devolvió el backend, con el
 * identificador como respaldo: un `Claims.name` ausente es normal en
 * proveedores que no lo emiten, y no debe dejar la barra sin identificar quién
 * tiene la sesión abierta.
 */
export function AppHeader({ onOpenNavigation }: AppHeaderProps): ReactElement {
  const { isAuthenticated, principal, logout } = useAuth();
  const displayName = principal?.identity.claims.name ?? principal?.identity.id;

  return (
    <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar>
        <IconButton
          color="inherit"
          edge="start"
          onClick={onOpenNavigation}
          aria-label="Abrir navegación"
          sx={{ mr: 2, display: { md: 'none' } }}
        >
          <MenuIcon />
        </IconButton>

        <Typography variant="h6" component="span" sx={{ flexGrow: 1 }}>
          TEAF
        </Typography>

        {isAuthenticated && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="body2" sx={{ display: { xs: 'none', sm: 'block' } }}>
              {displayName}
            </Typography>
            <Button color="inherit" onClick={() => void logout()}>
              Cerrar sesión
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}
