import type { UseQueryResult } from '@tanstack/react-query';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { ApiError } from '@/services';
import { renderWithProviders } from '@/test/render';

import { QueryBoundary } from './QueryBoundary';

/**
 * Construye un resultado de consulta con la forma que `QueryBoundary` consume.
 *
 * Se fabrica en vez de ejecutar una consulta real porque lo que se prueba aquí
 * es la decisión entre los cuatro estados, no la integración con TanStack Query
 * —esa se cubre en las pruebas de las pantallas.
 */
function queryResult<T>(overrides: Partial<UseQueryResult<T>>): UseQueryResult<T> {
  return {
    data: undefined,
    error: null,
    isPending: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  } as UseQueryResult<T>;
}

describe('QueryBoundary', () => {
  it('muestra el indicador de carga mientras la consulta está pendiente', () => {
    renderWithProviders(
      <QueryBoundary query={queryResult<string[]>({ isPending: true })}>
        {() => <p>Contenido</p>}
      </QueryBoundary>
    );

    expect(screen.getByRole('status')).toBeInTheDocument();
    expect(screen.queryByText('Contenido')).not.toBeInTheDocument();
  });

  it('muestra el error y permite reintentar', async () => {
    const refetch = vi.fn();
    const error = new ApiError({ type: 'about:blank', title: 'Bad Gateway', status: 502 });

    renderWithProviders(
      <QueryBoundary query={queryResult<string[]>({ isError: true, error, refetch })}>
        {() => <p>Contenido</p>}
      </QueryBoundary>
    );

    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));

    expect(refetch).toHaveBeenCalledOnce();
    expect(screen.queryByText('Contenido')).not.toBeInTheDocument();
  });

  it('distingue una colección vacía de un fallo', () => {
    renderWithProviders(
      <QueryBoundary
        query={queryResult<string[]>({ data: [] })}
        emptyTitle="No hay módulos"
        emptyDescription="Nada registrado."
      >
        {() => <p>Contenido</p>}
      </QueryBoundary>
    );

    expect(screen.getByText('No hay módulos')).toBeInTheDocument();
    expect(screen.getByText('Nada registrado.')).toBeInTheDocument();
    // Un listado vacío no es un error, y presentarlo como tal enseña al usuario
    // a desconfiar de los avisos que sí importan.
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('renderiza el contenido cuando hay datos', () => {
    renderWithProviders(
      <QueryBoundary query={queryResult<string[]>({ data: ['a', 'b'] })}>
        {(data) => <p>{data.length} elementos</p>}
      </QueryBoundary>
    );

    expect(screen.getByText('2 elementos')).toBeInTheDocument();
  });

  it('no considera vacío un objeto sin longitud', () => {
    renderWithProviders(
      <QueryBoundary query={queryResult<{ status: string }>({ data: { status: 'ok' } })}>
        {(data) => <p>Estado {data.status}</p>}
      </QueryBoundary>
    );

    expect(screen.getByText('Estado ok')).toBeInTheDocument();
  });

  it('admite un criterio de vacío propio', () => {
    renderWithProviders(
      <QueryBoundary
        query={queryResult<{ items: string[] }>({ data: { items: [] } })}
        isEmpty={(data) => data.items.length === 0}
        emptyTitle="Sin elementos"
      >
        {() => <p>Contenido</p>}
      </QueryBoundary>
    );

    expect(screen.getByText('Sin elementos')).toBeInTheDocument();
  });

  it('prioriza el error sobre el estado vacío', () => {
    // Tras un fallo, `data` sigue indefinida: sin este orden, el usuario vería
    // «no hay datos» cuando lo cierto es que la consulta falló.
    const error = new ApiError({ type: 'about:blank', title: 'Timeout', status: 504 });

    renderWithProviders(
      <QueryBoundary query={queryResult<string[]>({ isError: true, error })} emptyTitle="Vacío">
        {() => <p>Contenido</p>}
      </QueryBoundary>
    );

    expect(screen.queryByText('Vacío')).not.toBeInTheDocument();
    expect(screen.getByRole('alert')).toBeInTheDocument();
  });
});
