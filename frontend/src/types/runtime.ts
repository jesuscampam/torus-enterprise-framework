/**
 * Tipos de las respuestas de introspección que el backend TEAF ya emite.
 *
 * Cada interfaz de este archivo se corresponde con la salida real de un
 * endpoint, verificada contra la aplicación en ejecución — no con lo que sería
 * razonable que devolviera. Si el backend cambia, este archivo cambia detrás
 * (API First, ADR-004).
 *
 * **Nota de contrato**: estas colecciones se devuelven como arrays desnudos, no
 * con el sobre `CollectionEnvelope` de [API-STANDARD.md §4](../../../docs/standards/API-STANDARD.md).
 * Los endpoints `/runtime/*` son introspección del framework y preceden a ese
 * estándar; el frontend refleja lo que hay, no lo que debería haber.
 */

/** Estado del Runtime — `RuntimeState` en backend. */
export type RuntimeState = 'bootstrapping' | 'running' | 'stopped';

/** Madurez de un módulo — `ModuleStatus` en backend. */
export type ModuleStatus = 'contracts_only' | 'implemented' | 'deprecated';

/** `GET /` — identidad mínima de la instancia. */
export interface InstanceIdentity {
  name: string;
  version: string;
  environment: string;
}

/** Resumen de un módulo tal como lo emite `GET /info`. */
export interface ModuleSummary {
  name: string;
  version: string;
  status: string;
}

/** `GET /info` — versión, módulos y estado del Runtime. */
export interface FrameworkInfo extends InstanceIdentity {
  buildDate: string;
  modules: ModuleSummary[];
  state: RuntimeState;
  lifecycleStage: string | null;
  loadedModules: string[];
  registeredCapabilities: string[];
}

/** Desglose de salud por módulo — `CompositeHealthChecker.check_all()` en backend. */
export interface HealthReport {
  status: string;
  checks: Record<string, unknown>;
}

/** `GET /health` — estado general de la instancia. */
export interface HealthInfo extends InstanceIdentity {
  status: string;
  buildDate: string;
  modules: HealthReport;
}

/**
 * `GET /runtime/info` — diagnóstico del Runtime en vivo.
 *
 * `memoryRssBytes` y `cpuTimeSeconds` son opcionales porque el backend los
 * emite como `null` en plataformas donde `resource` no está disponible
 * (ver el parche de compatibilidad con Windows del Sprint 3.0).
 */
export interface RuntimeDiagnostics {
  runtimeId: string;
  startupTime: string | null;
  runningTimeSeconds: number;
  registeredModules: number;
  registeredServices: number;
  registeredCapabilities: number;
  registeredPlugins: number;
  registeredFeatures: number;
  frameworkVersion: string;
  pythonVersion: string;
  configurationSummary: Record<string, unknown>;
  dependencyGraphSummary: { nodes: number; edges: number };
  containerStatistics: Record<string, number>;
  memoryRssBytes: number | null;
  cpuTimeSeconds: number | null;
}

/** `GET /runtime/modules` — descriptor completo de un módulo registrado. */
export interface ModuleDescriptor {
  id: string;
  name: string;
  version: string;
  author: string | null;
  description: string;
  status: string;
  lifecycleState: string;
  capabilities: string[];
  dependencies: string[];
  tags: string[];
  documentation: string | null;
  experimental: boolean;
  createdAt: string;
  updatedAt: string;
}

/** `GET /runtime/events` — un evento del historial del `EventBus`. */
export interface RuntimeEvent {
  name: string;
  payload: Record<string, unknown>;
}

/** `GET /runtime/services` — metadata de un servicio del contenedor. */
export interface ServiceMetadata {
  serviceId: string;
  contract: string;
  lifetime: string;
  [field: string]: unknown;
}

/** `GET /runtime/capabilities` — metadata de una capacidad registrada. */
export interface CapabilityMetadata {
  id: string;
  name: string;
  [field: string]: unknown;
}

/** `GET /runtime/features` — un feature flag del framework. */
export interface FeatureFlag {
  id: string;
  name: string;
  description: string;
  group: string;
  status: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

/** `GET /runtime/plugins` — metadata de un plugin cargado. */
export interface PluginMetadata {
  name: string;
  version: string;
  [field: string]: unknown;
}
