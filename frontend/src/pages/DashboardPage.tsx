import { Box, Button, Card, CardContent, Chip, Grid, Typography } from '@mui/material';
import type { ReactElement } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { QueryBoundary } from '@/components/common/QueryBoundary';
import { useAuth } from '@/hooks/useAuth';
import { useHealth, useRuntimeDiagnostics } from '@/hooks/queries/useSystem';
import type { HealthInfo, RuntimeDiagnostics } from '@/types/runtime';

/** Convierte bytes a MiB con un decimal; `null` cuando la plataforma no lo mide. */
function formatMemory(bytes: number | null): string {
  if (bytes === null) return 'no disponible';
  return `${(bytes / 1024 / 1024).toFixed(1)} MiB`;
}

/** Segundos a un texto legible; el uptime en segundos crudos no dice nada a simple vista. */
function formatUptime(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)} s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min`;
  return `${Math.floor(seconds / 3600)} h ${Math.floor((seconds % 3600) / 60)} min`;
}

interface MetricProps {
  label: string;
  value: string | number;
}

function Metric({ label, value }: MetricProps): ReactElement {
  return (
    <Card variant="outlined" sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary" component="p">
          {label}
        </Typography>
        <Typography variant="h5" component="p">
          {value}
        </Typography>
      </CardContent>
    </Card>
  );
}

function HealthCard({ health }: { health: HealthInfo }): ReactElement {
  const healthy = health.status === 'ok';
  return (
    <Card variant="outlined">
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" component="h2">
            {health.name}
          </Typography>
          <Chip
            label={healthy ? 'Operativo' : 'Degradado'}
            color={healthy ? 'success' : 'warning'}
            size="small"
          />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Versión {health.version} · entorno {health.environment} · compilación {health.buildDate}
        </Typography>
      </CardContent>
    </Card>
  );
}

function RuntimeMetrics({ diagnostics }: { diagnostics: RuntimeDiagnostics }): ReactElement {
  // Solo contadores que el backend emite de verdad — ver `GET /runtime/info`.
  const metrics: MetricProps[] = [
    { label: 'Módulos', value: diagnostics.registeredModules },
    { label: 'Servicios', value: diagnostics.registeredServices },
    { label: 'Capacidades', value: diagnostics.registeredCapabilities },
    { label: 'Feature flags', value: diagnostics.registeredFeatures },
    { label: 'Plugins', value: diagnostics.registeredPlugins },
    { label: 'En ejecución', value: formatUptime(diagnostics.runningTimeSeconds) },
    { label: 'Memoria (RSS)', value: formatMemory(diagnostics.memoryRssBytes) },
    { label: 'Framework', value: diagnostics.frameworkVersion },
  ];

  return (
    <Grid container spacing={2}>
      {metrics.map((metric) => (
        <Grid key={metric.label} size={{ xs: 6, sm: 4, md: 3 }}>
          <Metric label={metric.label} value={metric.value} />
        </Grid>
      ))}
    </Grid>
  );
}

/**
 * Panel de entrada a la aplicación.
 *
 * Muestra **solo lo que el backend expone hoy**: salud de la instancia y los
 * contadores de `GET /runtime/info`. No hay KPIs de negocio porque TEAF es un
 * framework y no tiene negocio que medir (CLAUDE.md §1); inventarlos daría una
 * primera pantalla vistosa y falsa.
 */
export function DashboardPage(): ReactElement {
  const { principal } = useAuth();
  const health = useHealth();
  const diagnostics = useRuntimeDiagnostics();

  const greeting = principal?.identity.claims.name
    ? `Bienvenido, ${principal.identity.claims.name}`
    : 'Bienvenido';

  return (
    <Box>
      <PageHeader
        title={greeting}
        description="Estado de la instancia TEAF que sirve esta aplicación."
        actions={
          <Button
            variant="outlined"
            size="small"
            onClick={() => {
              void health.refetch();
              void diagnostics.refetch();
            }}
          >
            Actualizar
          </Button>
        }
      />

      <Box sx={{ mb: 3 }}>
        <QueryBoundary query={health} loadingLabel="Consultando estado del servicio…">
          {(data) => <HealthCard health={data} />}
        </QueryBoundary>
      </Box>

      <Typography variant="h6" component="h2" gutterBottom>
        Runtime
      </Typography>
      <QueryBoundary query={diagnostics} loadingLabel="Consultando el Runtime…">
        {(data) => <RuntimeMetrics diagnostics={data} />}
      </QueryBoundary>
    </Box>
  );
}
