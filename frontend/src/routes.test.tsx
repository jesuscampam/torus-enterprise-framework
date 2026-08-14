import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AppRoutes } from '@/routes';
import { httpClient } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { renderWithProviders } from '@/test/render';
import type { Principal } from '@/types/auth';

const principal: Principal = {
  identity: {
    id: 'u-1',
    providerId: 'jwt',
    claims: { subject: 'u-1', name: 'Ada' },
    authenticated: true,
  },
  roles: ['operator'],
  permissions: ['runtime:read'],
};

/** Sesión abierta, con las consultas del panel resueltas con datos mínimos. */
function authenticate(): void {
  useAuthStore.setState({ status: 'authenticated', principal, tokens: null, error: null });
}

function anonymous(): void {
  useAuthStore.setState({ status: 'anonymous', principal: null, tokens: null, error: null });
}

beforeEach(() => {
  anonymous();
  // Las pantallas privadas consultan el backend al montar; sin doblar el
  // cliente, cada prueba de navegación intentaría salir a la red.
  vi.spyOn(httpClient, 'get').mockImplementation((path: string) => {
    if (path === '/health') {
      return Promise.resolve({
        status: 'ok',
        name: 'TEAF',
        version: '0.10.3-alpha',
        environment: 'test',
        buildDate: 'unknown',
        modules: { status: 'healthy', checks: {} },
      });
    }
    if (path === '/runtime/info') {
      return Promise.resolve({
        runtimeId: 'r-1',
        startupTime: '2026-01-01T00:00:00Z',
        runningTimeSeconds: 12,
        registeredModules: 5,
        registeredServices: 0,
        registeredCapabilities: 0,
        registeredPlugins: 0,
        registeredFeatures: 0,
        frameworkVersion: '0.10.3-alpha',
        pythonVersion: '3.11.15',
        configurationSummary: {},
        dependencyGraphSummary: { nodes: 5, edges: 1 },
        containerStatistics: { registeredContracts: 0 },
        memoryRssBytes: 83333120,
        cpuTimeSeconds: 1.8,
      });
    }
    return Promise.resolve([]);
  });
  // El cierre de sesión avisa al backend antes de limpiar el estado local.
  vi.spyOn(httpClient, 'post').mockResolvedValue(undefined);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('Rutas públicas', () => {
  it('muestra el login sin sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/login' });

    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
  });

  it('monta el login sin la barra de la aplicación', async () => {
    renderWithProviders(<AppRoutes />, { route: '/login' });
    await screen.findByRole('heading', { name: 'Iniciar sesión' });

    // Una barra con «Cerrar sesión» sobre la pantalla de inicio de sesión no
    // describe ningún estado posible de la aplicación.
    expect(screen.queryByRole('button', { name: 'Cerrar sesión' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('navigation', { name: 'Navegación principal' })
    ).not.toBeInTheDocument();
  });

  it('muestra el destino de acceso denegado', async () => {
    renderWithProviders(<AppRoutes />, { route: '/forbidden' });

    expect(await screen.findByText('Acceso denegado')).toBeInTheDocument();
  });
});

describe('Ruta inexistente', () => {
  it('muestra la pantalla de no encontrada en vez de redirigir en silencio', async () => {
    renderWithProviders(<AppRoutes />, { route: '/esta-ruta-no-existe' });

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' })
    ).toBeInTheDocument();
    expect(screen.getByText('/esta-ruta-no-existe')).toBeInTheDocument();
  });

  it('también responde con sesión abierta', async () => {
    authenticate();
    renderWithProviders(<AppRoutes />, { route: '/tampoco-existe' });

    expect(
      await screen.findByRole('heading', { name: 'Página no encontrada' })
    ).toBeInTheDocument();
  });
});

describe('Rutas protegidas', () => {
  it('redirige al login cuando no hay sesión', async () => {
    renderWithProviders(<AppRoutes />, { route: '/modules' });

    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Módulos' })).not.toBeInTheDocument();
  });

  it('protege todas las rutas privadas, no solo la portada', async () => {
    for (const route of ['/', '/modules', '/events', '/runtime']) {
      anonymous();
      const { unmount } = renderWithProviders(<AppRoutes />, { route });

      expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
      unmount();
    }
  });

  it('muestra el panel cuando hay sesión', async () => {
    authenticate();
    renderWithProviders(<AppRoutes />, { route: '/' });

    expect(await screen.findByRole('heading', { name: 'Bienvenido, Ada' })).toBeInTheDocument();
  });

  it('espera sin decidir mientras se restaura la sesión', async () => {
    useAuthStore.setState({ status: 'authenticating' });
    renderWithProviders(<AppRoutes />, { route: '/modules' });

    expect(await screen.findByLabelText('Verificando sesión')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: 'Iniciar sesión' })).not.toBeInTheDocument();
  });
});

describe('Navegación', () => {
  it('ofrece la navegación principal dentro de la aplicación', async () => {
    authenticate();
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Bienvenido, Ada' });

    const navigation = screen.getByRole('navigation', { name: 'Navegación principal' });
    // El nombre accesible del enlace es «etiqueta + descripción», así que se
    // ancla al principio: sin el `^`, «Runtime» también casa con el enlace de
    // módulos, cuya descripción termina en «…en el Runtime».
    for (const label of ['Panel', 'Módulos', 'Eventos', 'Runtime']) {
      expect(
        within(navigation).getByRole('link', { name: new RegExp(`^${label}`) })
      ).toBeInTheDocument();
    }
  });

  it('navega entre pantallas sin recargar la aplicación', async () => {
    authenticate();
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Bienvenido, Ada' });

    const navigation = screen.getByRole('navigation', { name: 'Navegación principal' });
    await userEvent.click(within(navigation).getByRole('link', { name: /^Módulos/ }));

    expect(await screen.findByRole('heading', { level: 1, name: 'Módulos' })).toBeInTheDocument();
  });

  it('cierra la sesión desde la cabecera', async () => {
    authenticate();
    renderWithProviders(<AppRoutes />, { route: '/' });
    await screen.findByRole('heading', { name: 'Bienvenido, Ada' });

    await userEvent.click(screen.getByRole('button', { name: 'Cerrar sesión' }));

    await waitFor(() => {
      expect(useAuthStore.getState().status).toBe('anonymous');
    });
    expect(await screen.findByRole('heading', { name: 'Iniciar sesión' })).toBeInTheDocument();
  });
});
