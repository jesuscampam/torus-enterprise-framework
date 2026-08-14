import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, type ReactElement } from 'react';
import { BrowserRouter } from 'react-router-dom';

import { AppRoutes } from '@/routes';
import { ApiError } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { theme } from '@/theme';

/**
 * Construye una caché de estado de servidor con la política del framework.
 *
 * Es una fábrica y no una constante para que cada prueba pueda partir de una
 * caché limpia: compartir una sola instancia haría que el resultado de una
 * prueba se filtrara en la siguiente.
 */
export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: (failureCount, error) => {
          // Reintentar un 4xx es inútil: la petición está mal o falta permiso, y
          // repetirla da exactamente el mismo error. Solo se reintenta lo que
          // puede resolverse solo (fallos de red, 5xx transitorios).
          if (error instanceof ApiError && error.status < 500) return false;
          return failureCount < 2;
        },
      },
    },
  });
}

/**
 * Caché de la aplicación.
 *
 * Se crea fuera del componente a propósito: dentro, cada render produciría una
 * caché nueva y no habría caché en absoluto.
 */
const queryClient = createQueryClient();

export function App(): ReactElement {
  const restore = useAuthStore((state) => state.restore);

  // Rehidrata la sesión persistida al montar. Sin tokens guardados es un no-op.
  useEffect(() => {
    void restore();
  }, [restore]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
