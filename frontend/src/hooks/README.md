# hooks/

Hooks de React reutilizables entre páginas y componentes.

## Responsabilidad

- Encapsular lógica de estado y efectos reutilizable (por ejemplo, `useAuth`, `usePagination`, `useDebouncedValue`).
- Integrar `services/` y `store/` de forma reutilizable para componentes que necesitan datos o estado compartido.

## Qué NO debe contener

- Marcado JSX (los hooks no renderizan UI).
- Lógica de negocio específica de una única página (en ese caso, vive junto a la página en `pages/`).
