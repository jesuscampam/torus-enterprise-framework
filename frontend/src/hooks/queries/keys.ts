/**
 * Fábrica de claves de caché de TanStack Query.
 *
 * Existe para que la clave de una consulta se escriba **una sola vez**. Las
 * claves repetidas a mano son la causa habitual de dos bugs simétricos: una
 * invalidación que no refresca nada (clave distinta a la que se usó al leer) y
 * dos consultas que se pisan la caché (misma clave para datos distintos).
 *
 * La jerarquía es deliberada: `runtime.all` invalida todo el runtime de una
 * vez, y `runtime.events(limit)` solo esa consulta concreta.
 */
export const queryKeys = {
  system: {
    all: ['system'] as const,
    info: () => [...queryKeys.system.all, 'info'] as const,
    health: () => [...queryKeys.system.all, 'health'] as const,
  },
  runtime: {
    all: ['runtime'] as const,
    info: () => [...queryKeys.runtime.all, 'info'] as const,
    modules: () => [...queryKeys.runtime.all, 'modules'] as const,
    services: () => [...queryKeys.runtime.all, 'services'] as const,
    capabilities: () => [...queryKeys.runtime.all, 'capabilities'] as const,
    features: () => [...queryKeys.runtime.all, 'features'] as const,
    plugins: () => [...queryKeys.runtime.all, 'plugins'] as const,
    /** El `limit` entra en la clave: distinto límite es distinta respuesta. */
    events: (limit?: number) => [...queryKeys.runtime.all, 'events', { limit }] as const,
  },
} as const;
