/**
 * Consultas de estado de servidor contra los endpoints de sistema y de runtime.
 *
 * Todas pasan por el `httpClient` de `services/` — ningún componente llama a
 * `fetch` por su cuenta. Concentrarlas aquí es lo que permite que una pantalla
 * cambie de endpoint sin tocar JSX, y que la clave de caché y el tipo de la
 * respuesta viajen siempre juntos.
 */
import { useQuery, type UseQueryResult } from '@tanstack/react-query';

import { httpClient } from '@/services';
import type {
  CapabilityMetadata,
  FeatureFlag,
  FrameworkInfo,
  HealthInfo,
  ModuleDescriptor,
  PluginMetadata,
  RuntimeDiagnostics,
  RuntimeEvent,
  ServiceMetadata,
} from '@/types/runtime';

import { queryKeys } from './keys';

/** `GET /info` — versión, entorno y módulos declarados. */
export function useFrameworkInfo(): UseQueryResult<FrameworkInfo> {
  return useQuery({
    queryKey: queryKeys.system.info(),
    queryFn: ({ signal }) => httpClient.get<FrameworkInfo>('/info', { signal }),
  });
}

/**
 * `GET /health` — estado general de la instancia.
 *
 * La salud caduca antes que el resto: un dato de hace medio minuto no informa
 * de si el backend está sano *ahora*.
 */
export function useHealth(): UseQueryResult<HealthInfo> {
  return useQuery({
    queryKey: queryKeys.system.health(),
    queryFn: ({ signal }) => httpClient.get<HealthInfo>('/health', { signal }),
    staleTime: 5_000,
  });
}

/** `GET /runtime/info` — diagnóstico del Runtime (contadores, memoria, CPU). */
export function useRuntimeDiagnostics(): UseQueryResult<RuntimeDiagnostics> {
  return useQuery({
    queryKey: queryKeys.runtime.info(),
    queryFn: ({ signal }) => httpClient.get<RuntimeDiagnostics>('/runtime/info', { signal }),
    staleTime: 5_000,
  });
}

/** `GET /runtime/modules` — descriptores completos de los módulos registrados. */
export function useRuntimeModules(): UseQueryResult<ModuleDescriptor[]> {
  return useQuery({
    queryKey: queryKeys.runtime.modules(),
    queryFn: ({ signal }) => httpClient.get<ModuleDescriptor[]>('/runtime/modules', { signal }),
  });
}

/**
 * `GET /runtime/events` — historial del `EventBus`.
 *
 * `limit` es un parámetro real del backend, no un recorte del lado del cliente:
 * viaja como query param y el servidor devuelve solo esos eventos.
 */
export function useRuntimeEvents(limit?: number): UseQueryResult<RuntimeEvent[]> {
  return useQuery({
    queryKey: queryKeys.runtime.events(limit),
    queryFn: ({ signal }) =>
      httpClient.get<RuntimeEvent[]>('/runtime/events', {
        signal,
        ...(limit === undefined ? {} : { query: { limit } }),
      }),
    staleTime: 5_000,
  });
}

/** `GET /runtime/services` — servicios registrados en el contenedor. */
export function useRuntimeServices(): UseQueryResult<ServiceMetadata[]> {
  return useQuery({
    queryKey: queryKeys.runtime.services(),
    queryFn: ({ signal }) => httpClient.get<ServiceMetadata[]>('/runtime/services', { signal }),
  });
}

/** `GET /runtime/capabilities` — capacidades declaradas por los módulos. */
export function useRuntimeCapabilities(): UseQueryResult<CapabilityMetadata[]> {
  return useQuery({
    queryKey: queryKeys.runtime.capabilities(),
    queryFn: ({ signal }) =>
      httpClient.get<CapabilityMetadata[]>('/runtime/capabilities', { signal }),
  });
}

/** `GET /runtime/features` — feature flags del framework. */
export function useRuntimeFeatures(): UseQueryResult<FeatureFlag[]> {
  return useQuery({
    queryKey: queryKeys.runtime.features(),
    queryFn: ({ signal }) => httpClient.get<FeatureFlag[]>('/runtime/features', { signal }),
  });
}

/** `GET /runtime/plugins` — plugins cargados. */
export function useRuntimePlugins(): UseQueryResult<PluginMetadata[]> {
  return useQuery({
    queryKey: queryKeys.runtime.plugins(),
    queryFn: ({ signal }) => httpClient.get<PluginMetadata[]>('/runtime/plugins', { signal }),
  });
}
