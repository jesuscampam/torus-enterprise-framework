# core/

Kernel transversal del framework.

## Responsabilidad

- Bootstrap de la aplicación FastAPI: creación de la instancia, registro de routers, middlewares y manejadores de excepción.
- Contenedor de inyección de dependencias: provee las dependencias concretas (sesión de base de datos, repositorios, clientes externos) a `api/` y `services/` sin que estas capas las instancien directamente (principio Dependency Injection).
- Excepciones base y jerarquía de errores de dominio, consumidas por todas las capas.
- Gestión del ciclo de vida de la aplicación (startup/shutdown: apertura y cierre de conexiones, inicialización de observabilidad).

## Qué NO debe contener

- Lógica de negocio específica de una aplicación.
- Detalles de un dominio concreto (eso vive en `services/` y `models/`).

## Relación con otras capas

`core/` es consumido por prácticamente todas las capas, pero no depende de ninguna capa de negocio (`services/`, `repository/`, `models/`); solo de las capas transversales (`config/`, `monitoring/`).
