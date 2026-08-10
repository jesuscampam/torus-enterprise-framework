# Frontend — TEAF

Base reutilizable de frontend del framework, construida sobre **React + TypeScript + Material UI**
(ver [docs/architecture/STACK.md](../docs/architecture/STACK.md)) con el stack de arranque decidido
en [ADR-013](../docs/architecture/adr/ADR-013-enterprise-frontend-stack.md): **Vite**, **React
Router**, **Zustand**, **TanStack Query** y **Vitest**.

Estado: Sprint 3.5a (*core*) entregado — shell arrancable, cliente API tipado y autenticación.
La librería de componentes (3.5b) y el theming TORUS completo (3.5c) están pendientes; ver
[ROADMAP](../docs/roadmap/ROADMAP.md).

Arquitectura detallada: [docs/frontend/FRONTEND-ARCHITECTURE.md](../docs/frontend/FRONTEND-ARCHITECTURE.md).

## Puesta en marcha

```bash
cd frontend
npm install
cp .env.example .env      # ajusta las rutas de auth de tu aplicación
npm run dev               # http://localhost:5173 (proxy /api → :8000)
```

| Comando | Qué hace |
|---|---|
| `npm run dev` | Servidor de desarrollo con HMR. |
| `npm run build` | Comprueba tipos y genera el estático de producción en `dist/`. |
| `npm test` | Suite de pruebas (Vitest). |
| `npm run test:coverage` | Pruebas con informe de cobertura. |
| `npm run typecheck` | Solo comprobación de tipos. |
| `npm run lint` | ESLint con reglas que usan el type checker. |
| `npm run format` | Formatea con Prettier. |

## Estructura (`src/`)

| Carpeta | Responsabilidad |
|---|---|
| [`components/`](src/components/README.md) | Componentes UI reutilizables (design system base con Material UI). |
| [`pages/`](src/pages/README.md) | Vistas a nivel de ruta. |
| [`services/`](src/services/README.md) | Cliente API tipado, autenticación y almacenamiento de tokens. |
| [`hooks/`](src/hooks/README.md) | Hooks React reutilizables. |
| [`store/`](src/store/README.md) | Estado global **de cliente** (sesión, preferencias). |
| [`types/`](src/types/README.md) | Tipos e interfaces TypeScript compartidos. |
| [`utils/`](src/utils/README.md) | Utilidades genéricas de frontend. |
| [`theme/`](src/theme/README.md) | Configuración de tema Material UI. |
| [`config/`](src/config/README.md) | Configuración por entorno del frontend. |

## Principios rectores

**API First.** El frontend nunca accede a la base de datos ni conoce detalles de infraestructura del
backend; toda comunicación pasa por `src/services/`, consumiendo los contratos versionados de
`teaf/_internal/api/` (ver [ADR-004](../docs/architecture/adr/ADR-004-api-first.md)). Los tipos de
`src/types/` son espejo de esos contratos: si el backend cambia, cambian ellos detrás, nunca al revés.

**Estado de servidor ≠ estado de cliente.** Lo que vive en el backend se gestiona con TanStack Query
(caché, revalidación, reintentos); lo que solo existe en el navegador, con Zustand. Mezclarlos es el
antipatrón que [ADR-013 §3](../docs/architecture/adr/ADR-013-enterprise-frontend-stack.md) describe.

**La autorización de interfaz no sustituye a la del servidor.** `ProtectedRoute` evita mostrar
pantallas que el backend denegaría, pero la comprobación que manda es siempre la de
`SecurityMiddleware` + RBAC ([ADR-007](../docs/architecture/adr/ADR-007-enterprise-security-stack.md)).

**Ningún secreto en el bundle.** Solo las variables `VITE_` llegan al navegador y todas son públicas.
Ver [SECURITY-STANDARD.md](../docs/standards/SECURITY-STANDARD.md).
