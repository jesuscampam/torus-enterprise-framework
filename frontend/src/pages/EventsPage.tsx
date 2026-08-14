import { Box, Button, Paper, Stack, TextField, Typography } from '@mui/material';
import { useState, type FormEvent, type ReactElement } from 'react';

import { PageHeader } from '@/components/common/PageHeader';
import { QueryBoundary } from '@/components/common/QueryBoundary';
import { DataTable, type DataTableColumn } from '@/components/data/DataTable';
import { useRuntimeEvents } from '@/hooks/queries/useSystem';
import type { RuntimeEvent } from '@/types/runtime';

/** Límite máximo aceptado por el formulario; evita pedir un historial absurdo. */
const MAX_LIMIT = 500;

const columns: DataTableColumn<RuntimeEvent>[] = [
  {
    id: 'name',
    header: 'Evento',
    cell: (event) => (
      <Typography variant="body2" component="span" sx={{ fontFamily: 'monospace' }}>
        {event.name}
      </Typography>
    ),
  },
  {
    id: 'payload',
    header: 'Datos',
    cell: (event) => {
      const entries = Object.entries(event.payload);
      if (entries.length === 0) {
        return (
          <Typography variant="caption" color="text.secondary">
            —
          </Typography>
        );
      }
      return (
        <Typography variant="caption" component="span" sx={{ fontFamily: 'monospace' }}>
          {entries.map(([key, value]) => `${key}=${String(value)}`).join(' · ')}
        </Typography>
      );
    },
  },
];

/**
 * Valida el límite introducido.
 *
 * Devuelve el mensaje de error, o `null` si el valor es aceptable. Un campo
 * vacío es válido: significa «sin límite», que es como el backend interpreta la
 * ausencia del query param.
 */
function validateLimit(raw: string): string | null {
  if (raw.trim() === '') return null;

  const parsed = Number(raw);
  if (!Number.isInteger(parsed)) return 'Introduce un número entero.';
  if (parsed < 1) return 'El límite debe ser al menos 1.';
  if (parsed > MAX_LIMIT) return `El límite no puede superar ${MAX_LIMIT}.`;
  return null;
}

/**
 * Historial de eventos del `EventBus` (`GET /runtime/events`).
 *
 * El filtro de esta pantalla **no recorta en el cliente**: `limit` viaja como
 * query param y el backend devuelve solo esos eventos. Entra además en la clave
 * de caché, así que cada límite se cachea por separado y volver a uno ya
 * consultado no repite la petición.
 */
export function EventsPage(): ReactElement {
  // `draft` es lo que hay escrito en el campo; `limit` es lo ya aplicado. Sin
  // separarlos, cada tecla dispararía una petición nueva.
  const [draft, setDraft] = useState('');
  const [limit, setLimit] = useState<number | undefined>(undefined);
  const [validationError, setValidationError] = useState<string | null>(null);

  const events = useRuntimeEvents(limit);

  function handleSubmit(submitEvent: FormEvent<HTMLFormElement>): void {
    submitEvent.preventDefault();

    const error = validateLimit(draft);
    setValidationError(error);
    if (error) return;

    setLimit(draft.trim() === '' ? undefined : Number(draft));
  }

  function handleReset(): void {
    setDraft('');
    setValidationError(null);
    setLimit(undefined);
  }

  return (
    <Box>
      <PageHeader
        title="Eventos"
        description="Historial de eventos publicados en el EventBus del Runtime."
      />

      <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
        <form onSubmit={handleSubmit} aria-label="Filtrar eventos">
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={2}
            sx={{ alignItems: 'flex-start' }}
          >
            <TextField
              label="Número de eventos"
              value={draft}
              onChange={(changeEvent) => setDraft(changeEvent.target.value)}
              error={validationError !== null}
              helperText={validationError ?? `Vacío = todos. Máximo ${MAX_LIMIT}.`}
              size="small"
              inputMode="numeric"
              sx={{ minWidth: 220 }}
            />
            <Stack direction="row" spacing={1} sx={{ pt: 0.5 }}>
              <Button type="submit" variant="contained" size="medium">
                Aplicar
              </Button>
              <Button type="button" onClick={handleReset} size="medium">
                Limpiar
              </Button>
            </Stack>
          </Stack>
        </form>
      </Paper>

      <QueryBoundary
        query={events}
        loadingLabel="Cargando eventos…"
        emptyTitle="No hay eventos registrados"
        emptyDescription="El EventBus de esta instancia todavía no ha publicado nada."
      >
        {(data) => (
          <DataTable
            columns={columns}
            rows={data}
            // El EventBus no numera los eventos, así que la posición es la única
            // identidad disponible; basta porque el historial es inmutable y
            // solo crece por el final.
            rowKey={(event, index) => `${index}-${event.name}`}
            caption="Eventos publicados en el EventBus del Runtime, con sus datos asociados"
          />
        )}
      </QueryBoundary>
    </Box>
  );
}
