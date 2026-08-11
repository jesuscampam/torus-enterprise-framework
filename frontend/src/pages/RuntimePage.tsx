import { Box, Chip, Typography } from '@mui/material';
import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactElement } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { QueryBoundary } from '@/components/common/QueryBoundary';
import { DataTable, type DataTableColumn } from '@/components/data/DataTable';
import {
  useRuntimeCapabilities,
  useRuntimeFeatures,
  useRuntimePlugins,
  useRuntimeServices,
} from '@/hooks/queries/useSystem';
import type {
  CapabilityMetadata,
  FeatureFlag,
  PluginMetadata,
  ServiceMetadata,
} from '@/types/runtime';

const serviceColumns: DataTableColumn<ServiceMetadata>[] = [
  { id: 'contract', header: 'Contrato', cell: (service) => service.contract },
  { id: 'lifetime', header: 'Ciclo de vida', cell: (service) => service.lifetime },
];

const capabilityColumns: DataTableColumn<CapabilityMetadata>[] = [
  { id: 'id', header: 'Identificador', cell: (capability) => capability.id },
  { id: 'name', header: 'Nombre', cell: (capability) => capability.name },
];

const featureColumns: DataTableColumn<FeatureFlag>[] = [
  { id: 'name', header: 'Feature flag', cell: (feature) => feature.name },
  { id: 'group', header: 'Grupo', cell: (feature) => feature.group },
  {
    id: 'status',
    header: 'Estado',
    cell: (feature) => (
      <Chip
        label={feature.status === 'enabled' ? 'Activo' : 'Inactivo'}
        color={feature.status === 'enabled' ? 'success' : 'default'}
        size="small"
        variant="outlined"
      />
    ),
  },
];

const pluginColumns: DataTableColumn<PluginMetadata>[] = [
  { id: 'name', header: 'Plugin', cell: (plugin) => plugin.name },
  { id: 'version', header: 'Versión', cell: (plugin) => plugin.version },
];

interface InventorySectionProps<T> {
  title: string;
  query: UseQueryResult<T[]>;
  columns: DataTableColumn<T>[];
  rowKey: (row: T, index: number) => string;
  caption: string;
  emptyTitle: string;
  emptyDescription: string;
}

/** Una sección del inventario: encabezado, estados y tabla. */
function InventorySection<T>({
  title,
  query,
  columns,
  rowKey,
  caption,
  emptyTitle,
  emptyDescription,
}: InventorySectionProps<T>): ReactElement {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" component="h2" gutterBottom>
        {title}
      </Typography>
      <QueryBoundary
        query={query}
        loadingLabel={`Cargando ${title.toLowerCase()}…`}
        emptyTitle={emptyTitle}
        emptyDescription={emptyDescription}
      >
        {(data) => <DataTable columns={columns} rows={data} rowKey={rowKey} caption={caption} />}
      </QueryBoundary>
    </Box>
  );
}

/**
 * Inventario del Runtime: servicios, capacidades, feature flags y plugins.
 *
 * En un TEAF desnudo estas cuatro colecciones están vacías —solo se llenan
 * cuando una aplicación registra sus propios módulos—, así que la pantalla
 * muestra sobre todo estados vacíos. Eso es información legítima: dice que el
 * framework arrancó sin extensiones, que es distinto de que algo haya fallado.
 */
export function RuntimePage(): ReactElement {
  const services = useRuntimeServices();
  const capabilities = useRuntimeCapabilities();
  const features = useRuntimeFeatures();
  const plugins = useRuntimePlugins();

  return (
    <Box>
      <PageHeader
        title="Runtime"
        description="Servicios, capacidades, feature flags y plugins registrados en tiempo de ejecución."
      />

      <InventorySection
        title="Servicios"
        query={services}
        columns={serviceColumns}
        rowKey={(service, index) => `${index}-${service.contract}`}
        caption="Servicios registrados en el contenedor de dependencias"
        emptyTitle="No hay servicios registrados"
        emptyDescription="Los servicios aparecen aquí cuando un módulo los registra en el contenedor."
      />

      <InventorySection
        title="Capacidades"
        query={capabilities}
        columns={capabilityColumns}
        rowKey={(capability) => capability.id}
        caption="Capacidades declaradas por los módulos registrados"
        emptyTitle="No hay capacidades registradas"
        emptyDescription="Las capacidades las declara cada módulo en su manifiesto."
      />

      <InventorySection
        title="Feature flags"
        query={features}
        columns={featureColumns}
        rowKey={(feature) => feature.id}
        caption="Feature flags del framework, con su grupo y estado"
        emptyTitle="No hay feature flags registrados"
        emptyDescription="Esta instancia no declara ningún interruptor de funcionalidad."
      />

      <InventorySection
        title="Plugins"
        query={plugins}
        columns={pluginColumns}
        rowKey={(plugin, index) => `${index}-${plugin.name}`}
        caption="Plugins cargados por el Runtime"
        emptyTitle="No hay plugins cargados"
        emptyDescription="Los plugins se cargan explícitamente durante el arranque de la aplicación."
      />
    </Box>
  );
}
