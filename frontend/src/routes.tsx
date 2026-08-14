import { Suspense, lazy, type ReactElement } from 'react';
import { Route, Routes } from 'react-router-dom';

import { ProtectedRoute } from '@/components/ProtectedRoute';
import { LoadingState } from '@/components/common/LoadingState';
import { AppLayout } from '@/components/layout/AppLayout';
import { PublicLayout } from '@/components/layout/PublicLayout';
import { LoginPage } from '@/pages/LoginPage';

/**
 * Pantallas cargadas bajo demanda.
 *
 * El login y los layouts se importan de forma directa porque son lo primero que
 * ve cualquier visitante; el resto viaja en fragmentos aparte, que el navegador
 * solo descarga al navegar a ellos. Sin esto, todo el peso de las tablas y del
 * panel entra en el bundle inicial aunque el usuario se quede en el login.
 */
const DashboardPage = lazy(() =>
  import('@/pages/DashboardPage').then((module) => ({ default: module.DashboardPage }))
);
const ModulesPage = lazy(() =>
  import('@/pages/ModulesPage').then((module) => ({ default: module.ModulesPage }))
);
const EventsPage = lazy(() =>
  import('@/pages/EventsPage').then((module) => ({ default: module.EventsPage }))
);
const RuntimePage = lazy(() =>
  import('@/pages/RuntimePage').then((module) => ({ default: module.RuntimePage }))
);
const ForbiddenPage = lazy(() =>
  import('@/pages/ForbiddenPage').then((module) => ({ default: module.ForbiddenPage }))
);
const NotFoundPage = lazy(() =>
  import('@/pages/NotFoundPage').then((module) => ({ default: module.NotFoundPage }))
);

/**
 * Mapa de rutas de la aplicación, sin el router que las hospeda.
 *
 * Separarlo de `App` es lo que permite montarlo en las pruebas con un
 * `MemoryRouter` y una ruta inicial concreta; con el `BrowserRouter` dentro no
 * habría forma de comprobar una redirección sin tocar la URL del navegador.
 *
 * **Público arriba, privado abajo.** La guarda se aplica una sola vez, sobre el
 * layout que envuelve toda la rama privada: repetir `ProtectedRoute` en cada
 * ruta es la clase de duplicación en la que basta olvidarlo una vez para dejar
 * una pantalla abierta.
 */
export function AppRoutes(): ReactElement {
  return (
    <Suspense fallback={<LoadingState label="Cargando pantalla…" />}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/forbidden" element={<ForbiddenPage />} />
          {/* Ruta inexistente: se muestra, no se redirige en silencio. */}
          <Route path="*" element={<NotFoundPage />} />
        </Route>

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/" element={<DashboardPage />} />
          <Route path="/modules" element={<ModulesPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/runtime" element={<RuntimePage />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
