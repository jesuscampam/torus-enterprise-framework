/**
 * Recorrido completo del MVP (Sprint 3.5c).
 *
 * Es la prueba que ejercita la aplicación **entera**: pantallas, navegación,
 * store de sesión, hooks de consulta, `HttpClient` real y TanStack Query. Lo
 * único doblado es `fetch` (ver `test/fakeTeafServer.ts`), de modo que la
 * cadena que se recorre es la de producción:
 *
 * ```
 * Pantalla → hook de consulta → HttpClient → fetch → (doble de TEAF)
 * ```
 *
 * **Qué no cubre**: no hay navegador ni servidor reales. Es un recorrido de
 * extremo a extremo del frontend contra un backend simulado, no de la pila
 * desplegada — ver docs/frontend/FRONTEND-ARCHITECTURE.md §11 para la razón y
 * lo que quedaría por cubrir con un E2E de navegador.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '@/routes';
import { sessionBridge, tokenStorage } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { VALID_CREDENTIALS, createFakeTeafServer, type FakeServer } from '@/test/fakeTeafServer';
import { renderWithProviders } from '@/test/render';

let server: FakeServer;

/** Deja la aplicación como al abrirla por primera vez: sin sesión ni tokens. */
function resetSession(): void {
  useAuthStore.setState({ status: 'anonymous', principal: null, tokens: null, error: null });
  tokenStorage.clear();
  sessionBridge.setAccessToken(null);
}

beforeEach(() => {
  resetSession();
  server = createFakeTeafServer();
  vi.stubGlobal('fetch', server.fetch);
});

afterEach(() => {
  vi.unstubAllGlobals();
  resetSession();
});

/** Rellena el formulario de login y lo envía. */
async function signIn(): Promise<void> {
  await userEvent.type(screen.getByLabelText(/Usuario/), VALID_CREDENTIALS.username);
  await userEvent.type(screen.getByLabelText(/Contraseña/), VALID_CREDENTIALS.password);
  await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));
}

/** Navega por el menú lateral a la entrada indicada. */
async function navigateTo(label: string): Promise<void> {
  const navigation = screen.getByRole('navigation', { name: 'Navegación principal' });
  await userEvent.click(within(navigation).getByRole('link', { name: new RegExp(`^${label}`) }));
}

describe('Recorrido completo del MVP', () => {
  it('entra, recorre las cuatro pantallas y cierra sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/' });

    // 1. Sin sesión, la portada privada rebota al login.
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();

    // 2. Login con credenciales válidas.
    await signIn();

    // 3. El panel se pinta con datos que vienen del backend, no del store.
    expect(
      await screen.findByRole('heading', { name: 'Bienvenido, Ada Lovelace' })
    ).toBeInTheDocument();
    expect(await screen.findByText('Operativo')).toBeInTheDocument();
    expect(await screen.findByText('79.5 MiB')).toBeInTheDocument();

    // 4. Módulos: los cinco de infraestructura, con su dependencia declarada.
    await navigateTo('Módulos');
    expect(await screen.findByRole('heading', { level: 1, name: 'Módulos' })).toBeInTheDocument();
    const modulesTable = await screen.findByRole('table');
    expect(within(modulesTable).getByText('database')).toBeInTheDocument();
    expect(within(modulesTable).getByText('notification')).toBeInTheDocument();
    expect(within(modulesTable).getByText('security')).toBeInTheDocument();

    // 5. Eventos: el historial publicado durante el arranque.
    await navigateTo('Eventos');
    expect(await screen.findByRole('heading', { level: 1, name: 'Eventos' })).toBeInTheDocument();
    expect(await screen.findByText('framework.started')).toBeInTheDocument();

    // 6. Runtime: cuatro colecciones vacías, en estado vacío y no de error.
    await navigateTo('Runtime');
    expect(await screen.findByRole('heading', { level: 1, name: 'Runtime' })).toBeInTheDocument();
    expect(await screen.findByText('No hay servicios registrados')).toBeInTheDocument();
    expect(screen.getByText('No hay plugins cargados')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();

    // 7. Cierre de sesión: el backend se entera y la aplicación vuelve al login.
    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    await waitFor(() => {
      expect(server.hasSession()).toBe(false);
    });

    // 8. Y se puede volver a entrar. Se vuelve a «Runtime», que es donde estaba
    // el usuario al cerrar sesión: `ProtectedRoute` guarda el origen y el login
    // lo respeta, en lugar de devolver a todo el mundo a la portada.
    await signIn();
    expect(await screen.findByRole('heading', { level: 1, name: 'Runtime' })).toBeInTheDocument();
    expect(server.hasSession()).toBe(true);
  });

  it('adjunta el token a las llamadas al Runtime, no solo al login', async () => {
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    // El doble responde 401 sin `Authorization` válido, así que si el panel
    // muestra datos es porque el `HttpClient` adjuntó el token de verdad.
    const runtimeCalls = server.requests.filter((request) => request.path.startsWith('/runtime/'));
    expect(runtimeCalls.length).toBeGreaterThan(0);
  });

  it('envía una correlación distinta en cada petición', async () => {
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    const ids = server.requests.map((request) => request.correlationId);
    expect(ids.every((id) => id !== null && id.length > 0)).toBe(true);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('rechaza credenciales incorrectas sin abrir sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/login' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });

    await userEvent.type(screen.getByLabelText(/Usuario/), 'ada');
    await userEvent.type(screen.getByLabelText(/Contraseña/), 'equivocada');
    await userEvent.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeEnabled();
    expect(useAuthStore.getState().status).toBe('anonymous');
    expect(server.hasSession()).toBe(false);
  });
});

describe('Acceso sin sesión', () => {
  it.each(['/', '/modules', '/events', '/runtime'])(
    'redirige %s al login cuando no hay sesión',
    async (route) => {
      renderWithProviders(<AppRoutes />, { route });

      expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    }
  );

  it('lleva a la pantalla pedida después de iniciar sesión', async () => {
    // Entrar por `/events` sin sesión debe acabar en `/events`, no en la
    // portada: perder el destino obliga al usuario a repetir la navegación.
    renderWithProviders(<AppRoutes />, { route: '/events' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });

    await signIn();

    expect(await screen.findByRole('heading', { level: 1, name: 'Eventos' })).toBeInTheDocument();
  });

  it('no consulta el Runtime mientras no haya sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/modules' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });

    const runtimeCalls = server.requests.filter((request) => request.path.startsWith('/runtime/'));
    expect(runtimeCalls).toHaveLength(0);
  });
});

describe('Ruta inexistente', () => {
  it('muestra el 404 sin sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/no-existe' });

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' })
    ).toBeInTheDocument();
    expect(screen.getByText('/no-existe')).toBeInTheDocument();
  });

  it('muestra el 404 con sesión abierta y deja volver al panel', async () => {
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    // Se navega a mano porque ningún enlace de la aplicación lleva a una ruta
    // inexistente: el caso real es una URL escrita a mano o un enlace externo.
    window.history.pushState({}, '', '/no-existe');
    renderWithProviders(<AppRoutes />, { route: '/no-existe' });

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' })
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Volver al panel' })).toBeInTheDocument();
  });
});

describe('Restauración de sesión', () => {
  it('rehidrata la sesión guardada al abrir la aplicación', async () => {
    // Simula una recarga con tokens persistidos: el store los recupera y
    // pregunta al backend quién es el usuario antes de decidir nada.
    tokenStorage.write({
      accessToken: 'access-token-1',
      refreshToken: 'refresh-token-1',
      tokenType: 'Bearer',
      expiresIn: 900,
    });
    // El doble solo considera abierta la sesión tras un login; se abre una para
    // que el endpoint de identidad responda como tras una recarga real.
    await server.fetch('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(VALID_CREDENTIALS),
      headers: {},
    });

    renderWithProviders(<AppRoutes />, { route: '/modules' });
    await useAuthStore.getState().restore();

    expect(await screen.findByRole('heading', { level: 1, name: 'Módulos' })).toBeInTheDocument();
  });

  it('cierra la sesión si los tokens guardados ya no valen', async () => {
    tokenStorage.write({
      accessToken: 'token-caducado',
      refreshToken: 'refresh-caducado',
      tokenType: 'Bearer',
      expiresIn: 900,
    });

    renderWithProviders(<AppRoutes />, { route: '/modules' });
    await useAuthStore.getState().restore();

    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    expect(useAuthStore.getState().status).toBe('anonymous');
  });
});

describe('Degradación ante fallos del backend', () => {
  it('muestra el estado de error y permite reintentar', async () => {
    vi.unstubAllGlobals();
    server = createFakeTeafServer({ failing: ['/runtime/modules'] });
    vi.stubGlobal('fetch', server.fetch);

    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    await navigateTo('Módulos');

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
    // El mensaje es el genérico de servidor, no el detalle que envió el backend.
    expect(screen.queryByText(/Service Unavailable/)).not.toBeInTheDocument();
  });

  it('mantiene el panel utilizable si solo falla una de sus consultas', async () => {
    vi.unstubAllGlobals();
    server = createFakeTeafServer({ failing: ['/runtime/info'] });
    vi.stubGlobal('fetch', server.fetch);

    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();

    // La salud sigue viéndose aunque el diagnóstico del Runtime haya fallado.
    expect(await screen.findByText('Operativo')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('presenta las colecciones vacías como estado vacío, no como fallo', async () => {
    vi.unstubAllGlobals();
    server = createFakeTeafServer({ emptyCollections: true });
    vi.stubGlobal('fetch', server.fetch);

    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    await navigateTo('Módulos');

    expect(await screen.findByText('No hay módulos registrados')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('Filtro de eventos contra el servidor', () => {
  it('recorta en el backend, no en la tabla', async () => {
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });
    await signIn();
    await screen.findByText('Operativo');

    await navigateTo('Eventos');
    await screen.findByText('framework.started');
    expect(screen.getByText('framework.startup.completed')).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText(/Número de eventos/), '1');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));

    await waitFor(() => {
      expect(screen.queryByText('framework.startup.completed')).not.toBeInTheDocument();
    });
    expect(screen.getByText('framework.started')).toBeInTheDocument();
  });
});
