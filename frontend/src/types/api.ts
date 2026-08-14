/**
 * Tipos de los contratos HTTP que el backend TEAF ya emite.
 *
 * No se inventa nada aquí: cada tipo refleja un contrato definido en
 * `docs/standards/API-STANDARD.md`. Si el backend cambia, este archivo cambia
 * detrás — nunca al revés (API First, ADR-004).
 */

/**
 * Error según RFC 7807 (Problem Details), formato obligatorio de error en toda
 * API TEAF — ver API-STANDARD.md §6.
 *
 * `correlationId` es obligatorio en la respuesta del backend y es la pieza que
 * permite cruzar un error visto en el navegador con su traza en los logs del
 * servidor.
 */
export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  correlationId?: string;
}

/** Metadatos de paginación del sobre de colecciones — API-STANDARD.md §4. */
export interface PageMeta {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

/**
 * Sobre de respuesta de colecciones — API-STANDARD.md §4.
 *
 * Toda respuesta de colección lo usa; las respuestas de recurso único no.
 */
export interface CollectionEnvelope<T> {
  data: T[];
  meta: PageMeta;
}

/** Parámetros de paginación/orden aceptados como query params — API-STANDARD.md §5. */
export interface PageQuery {
  page?: number;
  pageSize?: number;
  sort?: string;
  order?: 'asc' | 'desc';
}

/** Métodos HTTP con la semántica estricta que exige API-STANDARD.md §3. */
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
