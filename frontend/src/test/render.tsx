import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement, ReactNode } from 'react';
import { MemoryRouter } from 'react-router-dom';

import { theme } from '@/theme';

interface RenderOptions {
  /** Ruta inicial del `MemoryRouter`. */
  route?: string;
}

/**
 * Cliente de consultas para pruebas.
 *
 * Sin reintentos: con la política de la aplicación, comprobar un estado de
 * error obligaría a esperar a que se agotaran, y la prueba tardaría segundos en
 * verificar algo instantáneo.
 */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, staleTime: 0, gcTime: 0 },
    },
  });
}

/**
 * Monta un componente con los proveedores que la aplicación le da en runtime.
 *
 * Existe para que una prueba no tenga que reconstruir el árbol de proveedores
 * —y para que, cuando ese árbol cambie, cambie en un solo sitio en vez de en
 * cada archivo de pruebas.
 */
export function renderWithProviders(ui: ReactElement, options: RenderOptions = {}): RenderResult {
  const { route = '/' } = options;
  const queryClient = createTestQueryClient();

  function Wrapper({ children }: { children: ReactNode }): ReactElement {
    return (
      <ThemeProvider theme={theme}>
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </QueryClientProvider>
      </ThemeProvider>
    );
  }

  return render(ui, { wrapper: Wrapper });
}
