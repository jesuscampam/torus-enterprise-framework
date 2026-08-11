import { Box, Button, Chip, Stack, Typography } from '@mui/material';
import type { ReactElement } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { QueryBoundary } from '@/components/common/QueryBoundary';
import { DataTable, type DataTableColumn } from '@/components/data/DataTable';
import { useRuntimeModules } from '@/hooks/queries/useSystem';
import type { ModuleDescriptor } from '@/types/runtime';

/** Color del estado del módulo — `ModuleStatus` en backend. */
function statusColor(status: string): 'success' | 'info' | 'default' {
  if (status === 'implemented') return 'success';
  if (status === 'contracts_only') return 'info';
  return 'default';
}

/** Etiqueta legible; el backend emite `snake_case` técnico. */
function statusLabel(status: string): string {
  if (status === 'implemented') return 'Implementado';
  if (status === 'contracts_only') return 'Solo contratos';
  return status;
}

const columns: DataTableColumn<ModuleDescriptor>[] = [
  {
    id: 'name',
    header: 'Módulo',
    cell: (module) => (
      <Box>
        <Typography variant="body2" component="span" sx={{ fontWeight: 'medium' }}>
          {module.name}
        </Typography>
        {module.description && (
          <Typography variant="caption" color="text.secondary" component="p">
            {module.description}
          </Typography>
        )}
      </Box>
    ),
  },
  { id: 'version', header: 'Versión', cell: (module) => module.version },
  {
    id: 'status',
    header: 'Estado',
    cell: (module) => (
      <Chip
        label={statusLabel(module.status)}
        color={statusColor(module.status)}
        size="small"
        variant="outlined"
      />
    ),
  },
  { id: 'lifecycle', header: 'Ciclo de vida', cell: (module) => module.lifecycleState },
  {
    id: 'dependencies',
    header: 'Dependencias',
    cell: (module) =>
      module.dependencies.length === 0 ? (
        <Typography variant="caption" color="text.secondary">
          —
        </Typography>
      ) : (
        <Stack direction="row" spacing={0.5} sx={{ flexWrap: 'wrap' }}>
          {module.dependencies.map((dependency) => (
            <Chip key={dependency} label={dependency} size="small" />
          ))}
        </Stack>
      ),
  },
];

/**
 * Módulos registrados en el Runtime (`GET /runtime/modules`).
 *
 * Es la pantalla que demuestra la tabla contra datos reales: el framework
 * registra cinco módulos de infraestructura al arrancar, cada uno con su estado
 * y sus dependencias declaradas.
 */
export function ModulesPage(): ReactElement {
  const modules = useRuntimeModules();

  return (
    <Box>
      <PageHeader
        title="Módulos"
        description="Módulos registrados en el Runtime de esta instancia."
        actions={
          <Button variant="outlined" size="small" onClick={() => void modules.refetch()}>
            Actualizar
          </Button>
        }
      />

      <QueryBoundary
        query={modules}
        loadingLabel="Cargando módulos…"
        emptyTitle="No hay módulos registrados"
        emptyDescription="Esta instancia arrancó sin ningún módulo en el registro."
      >
        {(data) => (
          <DataTable
            columns={columns}
            rows={data}
            rowKey={(module) => module.id}
            caption="Módulos registrados en el Runtime, con su versión, estado y dependencias"
          />
        )}
      </QueryBoundary>
    </Box>
  );
}
