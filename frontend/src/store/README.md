# store/

Gestión de estado global de la aplicación frontend.

## Responsabilidad

- Estado compartido entre múltiples páginas/componentes que no pertenece a un único componente (sesión de usuario autenticado, preferencias de UI, notificaciones globales).
- Punto único de verdad para el estado de autenticación consumido por `services/` (token JWT) y por rutas protegidas.

## Qué NO debe contener

- Estado local de un único componente (debe manejarse con el estado propio de React en `components/`/`pages/`).
- Datos que pueden derivarse directamente de una llamada a `services/` sin necesidad de compartirse globalmente.
