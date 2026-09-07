import { createTheme, type Theme } from '@mui/material/styles';

/**
 * Extiende la paleta de MUI con los tokens de superficie corporativos de TORUS
 * que no tienen equivalente semántico en la paleta estándar (`primary`,
 * `secondary`, `error`...). El gris de marca no es un color de acción ni de
 * estado: es un fondo de superficie (navegación, cabeceras de tabla), así que
 * vive en su propio namespace en vez de forzarlo dentro de `grey`, que MUI usa
 * internamente para estados deshabilitados y bordes.
 */
declare module '@mui/material/styles' {
  interface Palette {
    torus: { gray: string };
  }
  interface PaletteOptions {
    torus?: { gray: string };
  }
}

/**
 * Tema corporativo TORUS.
 *
 * Paleta extraída y verificada por contraste (WCAG AA) a partir de la
 * plantilla de marca oficial (`Plantilla de colores.pptx`, raíz del
 * repositorio):
 *
 * | Token              | Hex       | Contraste vs. blanco |
 * |--------------------|-----------|-----------------------|
 * | `primary.main`     | `#A02426` | 7.57:1                |
 * | `secondary.main`    | `#4A7007` | 5.81:1                |
 * | `secondary.light`   | `#5E8D09` | 3.97:1 (no para texto)|
 * | `text.primary`     | `#1F1F1F` | 16.48:1               |
 * | `torus.gray`       | `#D9D9D9` | uso solo de superficie|
 *
 * `secondary.light` conserva el verde original de marca para acentos no
 * textuales (iconografía, bordes); `secondary.main` es una versión oscurecida
 * porque el verde de marca puro no alcanza 4.5:1 sobre blanco y sí se usa como
 * texto (botones, enlaces).
 *
 * `error`/`success`/`warning`/`info` se dejan en los valores por defecto de
 * MUI a propósito: el rojo de marca es de identidad, no de estado, y
 * reutilizarlo como `error` mezclaría "esto es TORUS" con "esto ha fallado".
 *
 * Solo modo claro: el modo oscuro y las variantes por producto quedan fuera
 * de alcance hasta que una aplicación futura los necesite (CLAUDE.md §3).
 */
export const theme: Theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#A02426' },
    secondary: { main: '#4A7007', light: '#5E8D09' },
    text: { primary: '#1F1F1F' },
    torus: { gray: '#D9D9D9' },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
  },
  shape: {
    borderRadius: 8,
  },
});
