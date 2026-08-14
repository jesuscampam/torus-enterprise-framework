import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DashboardPage } from '@/pages/DashboardPage';
import { NetworkError, httpClient } from '@/services';
import { useAuthStore } from '@/store/authStore';
import { renderWithProviders } from '@/test/render';
import type { HealthInfo, RuntimeDiagnostics } from '@/types/runtime';

const health: HealthInfo = {
  status: 'ok',
  name: 'TEAF',
  version: '0.10.3-alpha',
  environment: 'development',
  buildDate: 'unknown',
  modules: { status: 'healthy', checks: {} },
};

const diagnostics: RuntimeDiagnostics = {
  runtimeId: 'r-1',
  startupTime: '2026-01-01T00:00:00Z',
  runningTimeSeconds: 125,
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
};

/** Responde cada endpoint del panel con su forma real. */
function stubBackend(overrides: { health?: unknown; runtime?: unknown } = {}) {
  return vi.spyOn(httpClient, 'get').mockImplementation((path: string) => {
    if (path === '/health') return Promise.resolve(overrides.health ?? health);
    if (path === '/runtime/info') return Promise.resolve(overrides.runtime ?? diagnostics);
    return Promise.resolve([]);
  });
}

beforeEach(() => {
  useAuthStore.setState({ status: 'authenticated', principal: null, tokens: null, error: null });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('DashboardPage', () => {
  it('muestra la identidad y el estado de la instancia', async () => {
    stubBackend();

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('TEAF')).toBeInTheDocument();
    expect(screen.getByText('Operativo')).toBeInTheDocument();
    expect(screen.getByText(/Versión 0.10.3-alpha/)).toBeInTheDocument();
  });

  it('señala una instancia degradada', async () => {
    stubBackend({ health: { ...health, status: 'degraded' } });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Degradado')).toBeInTheDocument();
  });

  it('muestra los contadores que el Runtime informa', async () => {
    stubBackend();

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('Módulos')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    // Formateado, no en segundos ni en bytes crudos.
    expect(screen.getByText('2 min')).toBeInTheDocument();
    expect(screen.getByText('79.5 MiB')).toBeInTheDocument();
  });

  it('declara la memoria como no disponible en plataformas que no la miden', async () => {
    // El backend emite `null` donde `resource` no existe (parche de Windows,
    // Sprint 3.0); inventar un número ahí sería mentir sobre la medición.
    stubBackend({ runtime: { ...diagnostics, memoryRssBytes: null } });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByText('no disponible')).toBeInTheDocument();
  });

  it('saluda por el nombre del Principal cuando el backend lo emite', async () => {
    stubBackend();
    useAuthStore.setState({
      principal: {
        identity: {
          id: 'u-1',
          providerId: 'jwt',
          claims: { subject: 'u-1', name: 'Ada' },
          authenticated: true,
        },
        roles: [],
        permissions: [],
      },
    });

    renderWithProviders(<DashboardPage />);

    expect(await screen.findByRole('heading', { name: 'Bienvenido, Ada' })).toBeInTheDocument();
  });

  it('degrada cada tarjeta por separado si una consulta falla', async () => {
    vi.spyOn(httpClient, 'get').mockImplementation((path: string) => {
      if (path === '/health') return Promise.resolve(health);
      return Promise.reject(new NetworkError('sin conexión'));
    });

    renderWithProviders(<DashboardPage />);

    // La salud sigue viéndose aunque el diagnóstico del Runtime haya fallado:
    // un panel que se apaga entero por una consulta caída informa menos.
    expect(await screen.findByText('Operativo')).toBeInTheDocument();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
