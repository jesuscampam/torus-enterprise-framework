import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { renderWithProviders } from '@/test/render';

import { DataTable, type DataTableColumn } from './DataTable';

interface Row {
  id: string;
  name: string;
  version: string;
}

const rows: Row[] = [
  { id: 'database', name: 'database', version: '0.10.3-alpha' },
  { id: 'storage', name: 'storage', version: '0.10.3-alpha' },
];

const columns: DataTableColumn<Row>[] = [
  { id: 'name', header: 'Módulo', cell: (row) => row.name },
  { id: 'version', header: 'Versión', cell: (row) => row.version },
];

describe('DataTable', () => {
  it('pinta una cabecera por columna y una fila por elemento', () => {
    renderWithProviders(
      <DataTable columns={columns} rows={rows} rowKey={(row) => row.id} caption="Módulos" />
    );

    expect(screen.getByRole('columnheader', { name: 'Módulo' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: 'Versión' })).toBeInTheDocument();

    // +1 por la fila de cabecera.
    expect(screen.getAllByRole('row')).toHaveLength(rows.length + 1);
    expect(screen.getByText('database')).toBeInTheDocument();
    expect(screen.getByText('storage')).toBeInTheDocument();
  });

  it('describe la tabla para lectores de pantalla', () => {
    renderWithProviders(
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(row) => row.id}
        caption="Módulos registrados en el Runtime"
      />
    );

    expect(
      screen.getByRole('table', { name: 'Módulos registrados en el Runtime' })
    ).toBeInTheDocument();
  });

  it('renderiza celdas con nodos, no solo texto', async () => {
    const onAction = vi.fn<(id: string) => void>();
    const withAction: DataTableColumn<Row>[] = [
      ...columns,
      {
        id: 'actions',
        header: 'Acciones',
        cell: (row) => <button onClick={() => onAction(row.id)}>Ver {row.name}</button>,
      },
    ];

    renderWithProviders(
      <DataTable columns={withAction} rows={rows} rowKey={(row) => row.id} caption="Módulos" />
    );

    await userEvent.click(screen.getByRole('button', { name: 'Ver database' }));

    expect(onAction).toHaveBeenCalledWith('database');
  });

  it('sostiene una tabla sin filas sin romperse', () => {
    // El estado vacío lo decide `QueryBoundary`; la tabla solo debe no fallar
    // si alguien la usa directamente con una colección vacía.
    renderWithProviders(
      <DataTable columns={columns} rows={[]} rowKey={(row) => row.id} caption="Módulos" />
    );

    expect(screen.getAllByRole('row')).toHaveLength(1);
  });

  it('usa el índice como clave en colecciones sin identificador propio', () => {
    // El historial del EventBus repite nombres de evento: sin el índice, dos
    // eventos iguales compartirían clave y React reutilizaría el nodo.
    const repeated = [
      { id: '', name: 'framework.started', version: '' },
      { id: '', name: 'framework.started', version: '' },
    ];

    renderWithProviders(
      <DataTable
        columns={columns}
        rows={repeated}
        rowKey={(row, index) => `${index}-${row.name}`}
        caption="Eventos"
      />
    );

    const table = screen.getByRole('table');
    expect(within(table).getAllByText('framework.started')).toHaveLength(2);
  });
});
