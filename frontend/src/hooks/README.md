# hooks/

Hooks de React reutilizables entre páginas y componentes.

## Responsabilidad

- Encapsular lógica de estado y efectos reutilizable (por ejemplo, `useAuth`, `usePagination`, `useDebouncedValue`).
- Integrar `services/` y `store/` de forma reutilizable para componentes que necesitan datos o estado compartido.

## Qué NO debe contener

- Marcado JSX (los hooks no renderizan UI).
- Lógica de negocio específica de una única página (en ese caso, vive junto a la página en `pages/`).

## Contenido actual

| Archivo | Qué aporta |
|---|---|
| `useAuth.ts` | Fachada sobre `store/authStore` para los componentes. |
| [`queries/keys.ts`](queries/) | Fábrica de claves de caché de TanStack Query. |
| [`queries/useSystem.ts`](queries/) | Consultas tipadas a los endpoints de sistema y de runtime. |

## Por qué las consultas viven aquí y no en las páginas

Toda consulta al backend pasa por `queries/useSystem.ts`, que a su vez usa el
`httpClient` de `services/`. Ninguna pantalla llama a `fetch` ni construye una
URL: así el tipo de la respuesta y la clave de caché viajan siempre juntos, y
cambiar un endpoint no obliga a tocar JSX.

Las **claves** salen de `queries/keys.ts` por la misma razón. Escribirlas a mano
en cada sitio produce dos fallos simétricos y silenciosos: una invalidación que
no refresca nada (clave distinta de la que se usó al leer) y dos consultas
distintas pisándose la caché (misma clave para datos distintos).
