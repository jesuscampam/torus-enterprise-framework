import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ApiError, NetworkError } from '@/services';
import { renderWithProviders } from '@/test/render';

import { EmptyState, EmptyStateAction } from './EmptyState';
import { ErrorState } from './ErrorState';
import { LoadingState } from './LoadingState';
import { PageHeader } from './PageHeader';

describe('LoadingState', () => {
  it('se anuncia como estado en curso a la tecnología asistiva', () => {
    renderWithProviders(<LoadingState />);

    // `role="status"` es lo que hace que un lector de pantalla lo anuncie sin
    // que el usuario tenga que ir a buscarlo.
    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.getByText('Cargando…')).toBeInTheDocument();
  });

  it('admite una etiqueta propia', () => {
    renderWithProviders(<LoadingState label="Consultando el Runtime…" />);

    expect(screen.getByText('Consultando el Runtime…')).toBeInTheDocument();
  });
});

describe('EmptyState', () => {
  it('muestra título y descripción', () => {
    renderWithProviders(
      <EmptyState title="No hay módulos" description="Nada registrado todavía." />
    );

    expect(screen.getByText('No hay módulos')).toBeInTheDocument();
    expect(screen.getByText('Nada registrado todavía.')).toBeInTheDocument();
  });

  it('ejecuta la acción ofrecida', async () => {
    const onClick = vi.fn();
    renderWithProviders(
      <EmptyState
        title="Sin datos"
        action={<EmptyStateAction label="Recargar" onClick={onClick} />}
      />
    );

    await userEvent.click(screen.getByRole('button', { name: 'Recargar' }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('no exige descripción ni acción', () => {
    renderWithProviders(<EmptyState title="Sin datos" />);

    expect(screen.getByText('Sin datos')).toBeInTheDocument();
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
});

describe('ErrorState', () => {
  it('traduce un 403 sin revelar qué permiso falta', () => {
    const error = new ApiError({
      type: 'about:blank',
      title: 'Forbidden',
      status: 403,
      detail: "Falta el permiso 'runtime:admin' del rol interno 'sre-lead'",
    });

    renderWithProviders(<ErrorState error={error} />);

    expect(
      screen.getByText('No tienes permisos para consultar esta información.')
    ).toBeInTheDocument();
    // El detalle del backend nombra permisos y roles internos: enumerarlos a
    // quien no está autorizado le da un mapa de lo que hay detrás.
    expect(screen.queryByText(/sre-lead/)).not.toBeInTheDocument();
  });

  it('resume un 500 sin volcar el detalle del servidor', () => {
    const error = new ApiError({
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      detail: 'psycopg2.OperationalError en teaf/_internal/repository/base.py línea 214',
    });

    renderWithProviders(<ErrorState error={error} />);

    expect(screen.getByText(/El servidor no pudo completar la petición/)).toBeInTheDocument();
    expect(screen.queryByText(/psycopg2/)).not.toBeInTheDocument();
  });

  it('explica un 4xx accionable con el detalle del backend', () => {
    const error = new ApiError({
      type: 'about:blank',
      title: 'Unprocessable Entity',
      status: 422,
      detail: 'El campo «limit» debe ser un entero positivo.',
    });

    renderWithProviders(<ErrorState error={error} />);

    expect(screen.getByText('El campo «limit» debe ser un entero positivo.')).toBeInTheDocument();
  });

  it('distingue un fallo de red de un error de la API', () => {
    renderWithProviders(<ErrorState error={new NetworkError('sin conexión')} />);

    expect(screen.getByText(/No se pudo contactar con el servidor/)).toBeInTheDocument();
  });

  it('muestra el correlationId para que soporte encuentre la traza', () => {
    const error = new ApiError({
      type: 'about:blank',
      title: 'Internal Server Error',
      status: 500,
      correlationId: 'abc-123',
    });

    renderWithProviders(<ErrorState error={error} />);

    expect(screen.getByText(/abc-123/)).toBeInTheDocument();
  });

  it('ofrece reintentar solo cuando hay algo que reintentar', async () => {
    const onRetry = vi.fn();
    const { rerender } = renderWithProviders(
      <ErrorState error={new NetworkError('sin conexión')} onRetry={onRetry} />
    );

    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(onRetry).toHaveBeenCalledOnce();

    rerender(<ErrorState error={new NetworkError('sin conexión')} />);
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
  });
});

describe('PageHeader', () => {
  it('publica el título como encabezado de nivel 1', () => {
    renderWithProviders(<PageHeader title="Módulos" description="Módulos registrados." />);

    expect(screen.getByRole('heading', { level: 1, name: 'Módulos' })).toBeInTheDocument();
    expect(screen.getByText('Módulos registrados.')).toBeInTheDocument();
  });

  it('renderiza las acciones que recibe', () => {
    renderWithProviders(<PageHeader title="Módulos" actions={<button>Actualizar</button>} />);

    expect(screen.getByRole('button', { name: 'Actualizar' })).toBeInTheDocument();
  });
});
