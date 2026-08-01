# Frontend — TEAF

Frontend del framework, construido sobre **React + TypeScript + Material UI** (ver [docs/architecture/STACK.md](../docs/architecture/STACK.md)).

> Esta iteración contiene únicamente la estructura de carpetas. El shell de aplicación ejecutable se incorpora en la Versión 3 del [roadmap](../docs/roadmap/ROADMAP.md).

## Estructura (`src/`)

| Carpeta | Responsabilidad |
|---|---|
| [`components/`](src/components/README.md) | Componentes UI reutilizables (design system base con Material UI). |
| [`pages/`](src/pages/README.md) | Vistas a nivel de ruta. |
| [`services/`](src/services/README.md) | Cliente API tipado hacia el backend. |
| [`hooks/`](src/hooks/README.md) | Hooks React reutilizables. |
| [`store/`](src/store/README.md) | Gestión de estado global. |
| [`types/`](src/types/README.md) | Tipos e interfaces TypeScript compartidos. |
| [`utils/`](src/utils/README.md) | Utilidades genéricas de frontend. |
| [`theme/`](src/theme/README.md) | Configuración de tema Material UI. |
| [`config/`](src/config/README.md) | Configuración por entorno del frontend. |

## Principio rector

El frontend nunca accede a la base de datos ni conoce detalles de infraestructura del backend; toda comunicación pasa por `src/services/`, consumiendo los contratos versionados definidos en `backend/api/` (principio API First, ver [ADR-004](../docs/architecture/adr/ADR-004-api-first.md)).
