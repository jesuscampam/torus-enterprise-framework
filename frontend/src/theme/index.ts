import { createTheme, type Theme } from '@mui/material/styles';

/**
 * Tema base de Material UI.
 *
 * **Alcance de Sprint 3.5a**: lo mínimo para que el shell arranque con identidad
 * coherente. La paleta corporativa TORUS completa, las variantes por producto y
 * el modo oscuro son Sprint 3.5c — no se adelantan aquí (CLAUDE.md §3: sin
 * sobre-ingeniería, nada de diseñar para requisitos que aún no están).
 */
export const theme: Theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#0B4F6C' },
    secondary: { main: '#01BAEF' },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
});
