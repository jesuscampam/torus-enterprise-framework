import { screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import { RuntimePage } from '@/pages/RuntimePage';
import { NetworkError, httpClient } from '@/services';
import { renderWithProviders } from '@/test/render';

let get: MockInstance<typeof httpClient.get>;

beforeEach(() => {
  get = vi.spyOn(httpClient, 'get');
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('RuntimePage', () => {
  it('consulta las cuatro colecciones del inventario', async () => {
    get.mockResolvedValue([]);

    renderWithProviders(<RuntimePage />);
    await screen.findByText('No hay servicios registrados');

    for (const path of [
      '/runtime/services',
      '/runtime/capabilities',
      '/runtime/features',
      '/runtime/plugins',
    ]) {
      expect(get).toHaveBeenCalledWith(path, expect.anything());
    }
  });

  it('presenta un inventario vacío como información, no como fallo', async () => {
    get.mockResolvedValue([]);

    renderWithProviders(<RuntimePage />);

    // Un TEAF sin extensiones tiene estas cuatro colecciones vacías: eso dice
    // que arrancó limpio, no que algo se rompiera.
    expect(await screen.findByText('No hay servicios registrados')).toBeInTheDocument();
    expect(screen.getByText('No hay capacidades registradas')).toBeInTheDocument();
    expect(screen.getByText('No hay feature flags registrados')).toBeInTheDocument();
    expect(screen.getByText('No hay plugins cargados')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('lista los feature flags con su estado', async () => {
    get.mockImplementation((path: string) => {
      if (path === '/runtime/features') {
        return Promise.resolve([
          {
            id: 'eventbus-distributed',
            name: 'Distributed Event Bus',
            description: '',
            group: 'platform',
            status: 'disabled',
            tags: [],
            createdAt: '2026-01-01T00:00:00Z',
            updatedAt: '2026-01-01T00:00:00Z',
          },
        ]);
      }
      return Promise.resolve([]);
    });

    renderWithProviders(<RuntimePage />);

    expect(await screen.findByText('Distributed Event Bus')).toBeInTheDocument();
    expect(screen.getByText('Inactivo')).toBeInTheDocument();
  });

  it('aísla el fallo de una sección sin tumbar las demás', async () => {
    get.mockImplementation((path: string) => {
      if (path === '/runtime/services') return Promise.reject(new NetworkError('sin conexión'));
      return Promise.resolve([]);
    });

    renderWithProviders(<RuntimePage />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('No hay capacidades registradas')).toBeInTheDocument();
  });
});
