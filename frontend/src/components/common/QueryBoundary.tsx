import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactElement } from 'react';

import { EmptyState } from './EmptyState';
import { ErrorState } from './ErrorState';
import { LoadingState } from './LoadingState';

interface QueryBoundaryProps<T> {
  /** El resultado tal cual lo devuelve `useQuery`. */
  query: UseQueryResult<T>;
  /** Se renderiza solo cuando hay datos y no están vacíos. */
  children: (data: T) => ReactElement;
  /** Decide si `data` cuenta como vacío. Por defecto, un array sin elementos. */
  isEmpty?: (data: T) => boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  loadingLabel?: string;
  errorTitle?: string;
}

/** Vacío por defecto: una colección sin elementos. Un objeto nunca lo está. */
function defaultIsEmpty(data: unknown): boolean {
  return Array.isArray(data) && data.length === 0;
}

/**
 * Resuelve los cuatro estados de una consulta en un único sitio.
 *
 * Sin esto, cada pantalla repite la misma escalera de `isPending` / `isError` /
 * «¿está vacío?» y las cuatro acaban divergiendo: una muestra un spinner, otra
 * un texto; una ofrece reintentar, otra no. El componente existe porque hay
 * cuatro pantallas reales consumiéndolo, no por si acaso.
 *
 * `children` es una función y no un nodo a propósito: así solo se invoca cuando
 * `data` existe, y TypeScript puede estrecharlo a `T` sin que cada pantalla
 * tenga que comprobar `data &&` de nuevo.
 */
export function QueryBoundary<T>({
  query,
  children,
  isEmpty = defaultIsEmpty,
  emptyTitle = 'No hay información disponible',
  emptyDescription,
  loadingLabel,
  errorTitle,
}: QueryBoundaryProps<T>): ReactElement {
  // El orden importa: durante un refetch tras un error, `isPending` ya es falso
  // pero todavía no hay datos — comprobar el error primero evita el parpadeo.
  if (query.isPending) {
    return <LoadingState {...(loadingLabel === undefined ? {} : { label: loadingLabel })} />;
  }

  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        onRetry={() => void query.refetch()}
        {...(errorTitle === undefined ? {} : { title: errorTitle })}
      />
    );
  }

  if (isEmpty(query.data)) {
    return (
      <EmptyState
        title={emptyTitle}
        {...(emptyDescription === undefined ? {} : { description: emptyDescription })}
      />
    );
  }

  return children(query.data);
}
