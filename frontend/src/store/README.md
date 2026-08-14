# store/

Gestión de estado global de la aplicación frontend.

## Responsabilidad

- Estado compartido entre múltiples páginas/componentes que no pertenece a un único componente (sesión de usuario autenticado, preferencias de UI, notificaciones globales).
- Punto único de verdad para el estado de autenticación consumido por `services/` (token JWT) y por rutas protegidas.

## Qué NO debe contener

- Estado local de un único componente (debe manejarse con el estado propio de React en `components/`/`pages/`).
- Datos que pueden derivarse directamente de una llamada a `services/` sin necesidad de compartirse globalmente.
- **Datos que viven en el backend** — ver la distinción de abajo.

## Estado de cliente vs. estado de servidor

La distinción que más deuda genera cuando se ignora ([ADR-013 §3](../../../docs/architecture/adr/ADR-013-enterprise-frontend-stack.md)):

| | Qué es | Con qué se gestiona |
|---|---|---|
| **Estado de cliente** | Solo existe en el navegador: sesión en curso, tema activo, estado del menú. | **Zustand** — esta carpeta. |
| **Estado de servidor** | Copia potencialmente obsoleta de algo que vive en el backend: listados, fichas, resultados. Necesita caché, revalidación e invalidación. | **TanStack Query** — se usa desde `hooks/` y `pages/`, no se guarda aquí. |

Meter una respuesta de la API en este store obliga a reimplementar a mano la caché, la
deduplicación y la invalidación que TanStack Query ya resuelve. Ese es el antipatrón que produce los
`useEffect` que llaman a `fetch` y escriben en el store.

## Implementación actual

`authStore.ts` — sesión: tokens, `Principal`, y las acciones `login`/`logout`/`restore`, más
`hasRole`/`hasPermission`. Registra además en el `SessionBridge` de `services/` el manejador con el
que el cliente HTTP renueva la sesión ante un 401.
