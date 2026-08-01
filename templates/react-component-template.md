# Plantilla — Componente React (`frontend/src/components/` o `frontend/src/pages/`)

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Código ilustrativo para copiar al implementar un componente real, conforme a [CODING-STANDARD.md](../docs/standards/CODING-STANDARD.md) (sección 2, Frontend).

## Cómo usar esta plantilla

1. Componentes funcionales con hooks, tipados estrictamente (`strict: true`), sin `any`.
2. Un componente por archivo, `PascalCase`.
3. Usa el tema de `frontend/src/theme/` para colores/tipografía — nunca valores "a mano".
4. Los datos llegan por props o por `hooks/`/`services/`; el componente de presentación no llama a `services/` directamente si puede evitarse.

```tsx
// frontend/src/components/{{NombreComponente}}.tsx
//
// Componente de ejemplo: {{descripción breve del propósito}}

import { FC } from "react";
import { Box, Typography } from "@mui/material";

export interface {{NombreComponente}}Props {
  /** TODO al implementar: describir cada prop */
  title: string;
  onAction?: () => void;
}

export const {{NombreComponente}}: FC<{{NombreComponente}}Props> = ({ title, onAction }) => {
  // Estado y efectos van aquí, vía hooks de frontend/src/hooks/ cuando sean reutilizables.

  return (
    <Box>
      <Typography variant="h6">{title}</Typography>
      {/* TODO al implementar: marcado real del componente, usando el theme de MUI */}
    </Box>
  );
};
```

## Qué NO hacer en este archivo

- No usar `any` ni props implícitas.
- No definir colores/tipografías fuera de `frontend/src/theme/`.
- No hacer `fetch`/`axios` directamente; usar `frontend/src/services/`.
