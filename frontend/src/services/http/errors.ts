import type { ProblemDetails } from '@/types/api';

/**
 * Error de una llamada a la API, con el Problem Details del backend intacto.
 *
 * Toda la aplicación captura este tipo y nunca inspecciona el `Response` en
 * bruto: el contrato de error del backend (RFC 7807, API-STANDARD.md §6) se
 * traduce aquí una sola vez.
 */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail ?? problem.title);
    this.name = 'ApiError';
    this.status = problem.status;
    this.problem = problem;
  }

  /** Identificador con el que rastrear este error en los logs del backend. */
  get correlationId(): string | undefined {
    return this.problem.correlationId;
  }

  /** `true` si la credencial falta, expiró o no es válida. */
  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  /** `true` si hay identidad pero le faltan permisos. */
  get isForbidden(): boolean {
    return this.status === 403;
  }

  /** `true` si el backend rechazó el payload — API-STANDARD.md §7. */
  get isValidationError(): boolean {
    return this.status === 422;
  }
}

/** Error de red o timeout: la petición nunca llegó a obtener respuesta. */
export class NetworkError extends Error {
  readonly cause: unknown;

  constructor(message: string, cause?: unknown) {
    super(message);
    this.name = 'NetworkError';
    this.cause = cause;
  }
}

/**
 * Construye un `ProblemDetails` a partir de una respuesta de error.
 *
 * El backend TEAF siempre responde en RFC 7807, pero un frontend empresarial
 * también recibe errores de piezas que no son el backend —un proxy inverso, un
 * balanceador, un gateway de Azure— que responden HTML o texto plano. Cuando el
 * cuerpo no es un Problem Details válido se sintetiza uno, de modo que el resto
 * de la aplicación nunca tenga que distinguir ambos casos.
 */
export async function toProblemDetails(
  response: Response,
  correlationId: string
): Promise<ProblemDetails> {
  const fallback: ProblemDetails = {
    type: 'about:blank',
    title: response.statusText || 'Error de API',
    status: response.status,
    correlationId,
  };

  try {
    const body: unknown = await response.json();
    if (typeof body !== 'object' || body === null) return fallback;

    const problem = body as Partial<ProblemDetails>;
    // `status` y `title` son obligatorios en RFC 7807; si faltan, el cuerpo no
    // era un Problem Details y se prefiere lo que dice la respuesta HTTP.
    if (typeof problem.title !== 'string' || typeof problem.status !== 'number') {
      return fallback;
    }

    return {
      ...problem,
      type: problem.type ?? 'about:blank',
      title: problem.title,
      status: problem.status,
      // El backend siempre lo envía; si un intermediario lo perdió, se conserva
      // el generado por el cliente para no romper la cadena de trazabilidad.
      correlationId: problem.correlationId ?? correlationId,
    };
  } catch {
    return fallback;
  }
}
