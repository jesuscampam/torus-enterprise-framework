import CssBaseline from '@mui/material/CssBaseline';
import { ThemeProvider } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, type ReactElement } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';

import { AppLayout } from '@/components/AppLayout';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { ForbiddenPage } from '@/pages/ForbiddenPage';
import { HomePage } from '@/pages/HomePage';
import { LoginPage } from '@/pages/LoginPage';
import { ApiError } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { theme } from '@/theme';

/**
 * Caché de estado de servidor.
 *
 * Se crea fuera del componente a propósito: dentro, cada render produciría una
 * caché nueva y no habría caché en absoluto.
 */
const queryClient = new QueryClient({
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
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/forbidden" element={<ForbiddenPage />} />
              <Route
                path="/"
                element={
                  <ProtectedRoute>
                    <HomePage />
                  </ProtectedRoute>
                }
              />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  );
}
