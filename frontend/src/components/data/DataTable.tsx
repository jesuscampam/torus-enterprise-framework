import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import type { ReactElement, ReactNode } from 'react';

/**
 * Oculta visualmente sin ocultar a un lector de pantalla.
 *
 * `display: none` o `visibility: hidden` lo esconderían también de la
 * tecnología asistiva, que es justo lo contrario de lo que se busca aquí.
 */
const visuallyHidden = {
  position: 'absolute',
  width: 1,
  height: 1,
  overflow: 'hidden',
  clip: 'rect(0 0 0 0)',
  whiteSpace: 'nowrap',
} as const;

/** Descripción de una columna: cómo se titula y cómo se extrae su celda. */
export interface DataTableColumn<T> {
  /** Identificador estable de la columna; se usa como `key` de React. */
  id: string;
  header: string;
  /** Extrae el contenido de la celda para una fila. */
  cell: (row: T) => ReactNode;
  align?: 'left' | 'right' | 'center';
}

interface DataTableProps<T> {
  columns: DataTableColumn<T>[];
  rows: T[];
  /**
   * Clave estable de cada fila. Sin ella React reordena mal al refrescar.
   *
   * Recibe también el índice para las colecciones sin identificador propio
   * (el historial del EventBus, por ejemplo, no numera sus eventos).
   */
  rowKey: (row: T, index: number) => string;
  /** Descripción de la tabla para lectores de pantalla. */
  caption: string;
}

/**
 * Tabla de datos tipada.
 *
 * Recibe los datos ya resueltos: **no consulta nada**. Los estados de carga,
 * error y vacío los decide `QueryBoundary` antes de llegar aquí, de modo que
 * este componente tiene una sola responsabilidad y se puede probar con datos
 * literales.
 *
 * `cell` devuelve un nodo en vez de una cadena para que una columna pueda pintar
 * un `Chip` de estado o un enlace sin que la tabla necesite saber de tipos
 * especiales de columna.
 *
 * **Sin paginación**: los endpoints que consume hoy devuelven la colección
 * completa, sin `meta` de paginación. Añadir controles de página aquí simularía
 * una capacidad que el backend no tiene (ver `types/runtime.ts`).
 */
export function DataTable<T>({ columns, rows, rowKey, caption }: DataTableProps<T>): ReactElement {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <Box component="caption" sx={visuallyHidden}>
          {caption}
        </Box>
        <TableHead>
          <TableRow>
            {columns.map((column) => (
              <TableCell key={column.id} align={column.align ?? 'left'} component="th" scope="col">
                {column.header}
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map((row, index) => (
            <TableRow key={rowKey(row, index)} hover>
              {columns.map((column) => (
                <TableCell key={column.id} align={column.align ?? 'left'}>
                  {column.cell(row)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
