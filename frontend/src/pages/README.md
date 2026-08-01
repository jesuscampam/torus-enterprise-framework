# pages/

Vistas a nivel de ruta (componentes de página).

## Responsabilidad

- Componer `components/` para formar una vista completa asociada a una ruta.
- Orquestar la obtención de datos mediante `services/` y `hooks/`, y gestionar el estado local de la página.

## Qué NO debe contener

- Lógica de UI genérica reutilizable (debe extraerse a `components/`).
- Llamadas HTTP directas (deben pasar por `services/`).
