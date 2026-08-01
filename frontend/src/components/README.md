# components/

Componentes de interfaz reutilizables — la base del design system común a todas las aplicaciones TORUS construidas sobre TEAF.

## Responsabilidad

- Componentes de presentación genéricos construidos sobre Material UI (tablas de datos, formularios, layout, navegación).
- Componentes sin conocimiento de una página o flujo de negocio específico; reciben datos y callbacks vía props.

## Qué NO debe contener

- Llamadas directas a `services/` (la obtención de datos ocurre en `pages/` o mediante `hooks/`, que pasan los datos como props).
- Lógica de negocio específica de una aplicación concreta.
