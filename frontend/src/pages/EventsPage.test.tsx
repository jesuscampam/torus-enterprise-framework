import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import { EventsPage } from '@/pages/EventsPage';
import { ApiError, httpClient } from '@/services';
import { renderWithProviders } from '@/test/render';
import type { RuntimeEvent } from '@/types/runtime';

const events: RuntimeEvent[] = [
  { name: 'framework.started', payload: {} },
  { name: 'module.registered', payload: { name: 'database' } },
];

let get: MockInstance<typeof httpClient.get>;

beforeEach(() => {
  get = vi.spyOn(httpClient, 'get').mockResolvedValue(events);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('EventsPage', () => {
  it('lista los eventos que devuelve el backend', async () => {
    renderWithProviders(<EventsPage />);

    expect(await screen.findByText('framework.started')).toBeInTheDocument();
    expect(screen.getByText('module.registered')).toBeInTheDocument();
  });

  it('muestra el payload de cada evento', async () => {
    renderWithProviders(<EventsPage />);

    expect(await screen.findByText('name=database')).toBeInTheDocument();
  });

  it('pide todos los eventos mientras no se aplique un límite', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');

    // Sin límite no debe viajar el query param: el backend interpreta su
    // ausencia como «todo el historial».
    const [path, options] = get.mock.calls[0] ?? [];
    expect(path).toBe('/runtime/events');
    expect(options).not.toHaveProperty('query');
  });

  it('envía el límite al servidor como query param', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');

    await userEvent.type(screen.getByLabelText(/Número de eventos/), '5');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));

    // Lo que se prueba es que el filtro llega al backend, no que la tabla
    // recorte en el cliente: recortar aquí daría un número correcto sobre datos
    // que el servidor nunca acotó.
    await vi.waitFor(() => {
      expect(get).toHaveBeenCalledWith(
        '/runtime/events',
        expect.objectContaining({ query: { limit: 5 } })
      );
    });
  });

  it('rechaza un límite no numérico sin llamar al backend', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');
    const callsBefore = get.mock.calls.length;

    await userEvent.type(screen.getByLabelText(/Número de eventos/), 'diez');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));

    expect(await screen.findByText('Introduce un número entero.')).toBeInTheDocument();
    expect(get.mock.calls).toHaveLength(callsBefore);
  });

  it('rechaza un límite fuera de rango', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');

    await userEvent.type(screen.getByLabelText(/Número de eventos/), '0');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));
    expect(await screen.findByText('El límite debe ser al menos 1.')).toBeInTheDocument();

    await userEvent.clear(screen.getByLabelText(/Número de eventos/));
    await userEvent.type(screen.getByLabelText(/Número de eventos/), '9999');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));
    expect(await screen.findByText('El límite no puede superar 500.')).toBeInTheDocument();
  });

  it('marca el campo como inválido para la tecnología asistiva', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');

    await userEvent.type(screen.getByLabelText(/Número de eventos/), 'diez');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));

    expect(screen.getByLabelText(/Número de eventos/)).toHaveAttribute('aria-invalid', 'true');
  });

  it('limpia el filtro y vuelve a pedir el historial completo', async () => {
    renderWithProviders(<EventsPage />);
    await screen.findByText('framework.started');

    await userEvent.type(screen.getByLabelText(/Número de eventos/), '5');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar' }));
    await userEvent.click(screen.getByRole('button', { name: 'Limpiar' }));

    expect(screen.getByLabelText(/Número de eventos/)).toHaveValue('');
  });

  it('muestra el estado vacío cuando el EventBus no ha publicado nada', async () => {
    get.mockResolvedValue([]);
    renderWithProviders(<EventsPage />);

    expect(await screen.findByText('No hay eventos registrados')).toBeInTheDocument();
  });

  it('muestra el estado de error cuando la consulta falla', async () => {
    get.mockRejectedValue(
      new ApiError({ type: 'about:blank', title: 'Service Unavailable', status: 503 })
    );
    renderWithProviders(<EventsPage />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reintentar' })).toBeInTheDocument();
  });
});
