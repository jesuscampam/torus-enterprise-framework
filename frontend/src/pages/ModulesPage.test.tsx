import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import { ModulesPage } from '@/pages/ModulesPage';
import { ApiError, NetworkError, httpClient } from '@/services';
import { renderWithProviders } from '@/test/render';
import type { ModuleDescriptor } from '@/types/runtime';

/** Descriptor con la forma exacta que emite `GET /runtime/modules`. */
function moduleDescriptor(overrides: Partial<ModuleDescriptor> = {}): ModuleDescriptor {
  return {
    id: 'database',
    name: 'database',
    version: '0.10.3-alpha',
    author: null,
    description: '',
    status: 'contracts_only',
    lifecycleState: 'registered',
    capabilities: [],
    dependencies: [],
    tags: [],
    documentation: null,
    experimental: false,
    createdAt: '2026-01-01T00:00:00Z',
    updatedAt: '2026-01-01T00:00:00Z',
    ...overrides,
  };
}

let get: MockInstance<typeof httpClient.get>;

beforeEach(() => {
  get = vi.spyOn(httpClient, 'get');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('ModulesPage', () => {
  it('pinta un módulo por fila con su versión y estado', async () => {
    get.mockResolvedValue([
      moduleDescriptor(),
      moduleDescriptor({ id: 'ai', name: 'ai', dependencies: ['security'] }),
    ]);

    renderWithProviders(<ModulesPage />);

    expect(await screen.findByRole('table')).toBeInTheDocument();
    expect(screen.getByText('database')).toBeInTheDocument();
    expect(screen.getByText('ai')).toBeInTheDocument();
    expect(screen.getByText('security')).toBeInTheDocument();
  });

  it('traduce el estado técnico del backend', async () => {
    get.mockResolvedValue([
      moduleDescriptor({ status: 'implemented' }),
      moduleDescriptor({ id: 'ai', name: 'ai', status: 'contracts_only' }),
    ]);

    renderWithProviders(<ModulesPage />);

    // `contracts_only` es el vocabulario del backend, no del usuario.
    expect(await screen.findByText('Implementado')).toBeInTheDocument();
    expect(screen.getByText('Solo contratos')).toBeInTheDocument();
  });

  it('muestra el estado vacío cuando no hay módulos', async () => {
    get.mockResolvedValue([]);

    renderWithProviders(<ModulesPage />);

    expect(await screen.findByText('No hay módulos registrados')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('muestra el estado de error y permite reintentar', async () => {
    get.mockRejectedValue(new NetworkError('sin conexión'));

    renderWithProviders(<ModulesPage />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText(/No se pudo contactar con el servidor/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
  });

  it('no revela el detalle interno de un error de servidor', async () => {
    get.mockRejectedValue(
      new ApiError({
        type: 'about:blank',
        title: 'Internal Server Error',
        status: 500,
        detail: 'Traceback en teaf/_internal/runtime/runtime.py línea 88',
      })
    );

    renderWithProviders(<ModulesPage />);

    await screen.findByRole('alert');
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument();
  });

  it('vuelve a consultar el backend al pulsar Actualizar', async () => {
    get.mockResolvedValue([moduleDescriptor()]);

    renderWithProviders(<ModulesPage />);
    await screen.findByRole('table');
    const callsBefore = get.mock.calls.length;

    await userEvent.click(screen.getByRole('button', { name: 'Actualizar' }));

    await vi.waitFor(() => {
      expect(get.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it('consulta el endpoint real del Runtime', async () => {
    get.mockResolvedValue([]);

    renderWithProviders(<ModulesPage />);
    await screen.findByText('No hay módulos registrados');

    expect(get).toHaveBeenCalledWith('/runtime/modules', expect.anything());
  });
});
