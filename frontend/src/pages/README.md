# pages/

Vistas a nivel de ruta (componentes de página).

## Responsabilidad

- Componer `components/` para formar una vista completa asociada a una ruta.
- Orquestar la obtención de datos mediante `services/` y `hooks/`, y gestionar el estado local de la página.

## Qué NO debe contener

- Lógica de UI genérica reutilizable (debe extraerse a `components/`).
- Llamadas HTTP directas (deben pasar por `services/`).

## Pantallas actuales

| Pantalla | Ruta | Datos que consume |
|---|---|---|
| `LoginPage` | `/login` (pública) | Rutas de autenticación de la aplicación anfitriona (configurables). |
| `DashboardPage` | `/` | `GET /health` y `GET /runtime/info`. |
| `ModulesPage` | `/modules` | `GET /runtime/modules`. |
| `EventsPage` | `/events` | `GET /runtime/events`, con `?limit=` real. |
| `RuntimePage` | `/runtime` | `GET /runtime/{services,capabilities,features,plugins}`. |
| `ForbiddenPage` | `/forbidden` (pública) | — |
| `NotFoundPage` | `*` (pública) | — |

El mapa de rutas vive en [`src/routes.tsx`](../routes.tsx).

## Solo se muestra lo que el backend expone

TEAF es un framework, no una aplicación: no tiene negocio que medir ni CRUD que
ofrecer, y **todos sus endpoints son de solo lectura**. Por eso el panel enseña
salud y contadores del Runtime en vez de KPIs, y no hay formularios de alta o
edición. Inventarlos daría pantallas más vistosas y falsas.

Las aplicaciones construidas sobre TEAF sí añaden sus propias pantallas de
negocio, en sus propios repositorios (CLAUDE.md §1 y §10).
