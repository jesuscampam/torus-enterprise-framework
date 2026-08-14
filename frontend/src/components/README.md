# components/

Componentes de interfaz reutilizables — la base del design system común a todas las aplicaciones TORUS construidas sobre TEAF.

## Responsabilidad

- Componentes de presentación genéricos construidos sobre Material UI (tablas de datos, formularios, layout, navegación).
- Componentes sin conocimiento de una página o flujo de negocio específico; reciben datos y callbacks vía props.

## Qué NO debe contener

- Llamadas directas a `services/` (la obtención de datos ocurre en `pages/` o mediante `hooks/`, que pasan los datos como props).
- Lógica de negocio específica de una aplicación concreta.

## Organización (Sprint 3.5b)

| Carpeta | Contiene |
|---|---|
| [`layout/`](layout/) | Marco de la aplicación: `AppLayout`, `AppHeader`, `AppNavigation`, `PublicLayout` y la lista de entradas de navegación. |
| [`common/`](common/) | Estados transversales de pantalla: `PageHeader`, `LoadingState`, `EmptyState`, `ErrorState` y `QueryBoundary`. |
| [`data/`](data/) | Presentación de datos: `DataTable`. |
| raíz | `ProtectedRoute` — guarda de ruta, no encaja en ninguna de las tres anteriores. |

### `QueryBoundary` es el punto de entrada habitual

Las pantallas no encadenan `isPending` / `isError` / «¿está vacío?» a mano: le pasan
el resultado de la consulta a `QueryBoundary` y este decide cuál de los cuatro
estados corresponde. Es lo que mantiene idénticos el spinner, el mensaje de vacío
y el de error en todas las pantallas.

```tsx
<QueryBoundary query={modules} emptyTitle="No hay módulos registrados">
  {(data) => <DataTable columns={columns} rows={data} rowKey={(m) => m.id} caption="…" />}
</QueryBoundary>
```

`DataTable` recibe los datos **ya resueltos**: no consulta nada y no conoce los
estados de carga. Esa separación es la que permite probarla con datos literales.

## Dos layouts, no uno

`AppLayout` (privado, con cabecera y navegación) y `PublicLayout` (login, 403 y 404)
son distintos a propósito: una barra con el botón «Cerrar sesión» sobre la pantalla
de inicio de sesión no describe ningún estado posible de la aplicación.
