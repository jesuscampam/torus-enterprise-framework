# docker/frontend/

Ubicación reservada para el `Dockerfile` del frontend (React + TypeScript).

## Alcance previsto (Versión 1)

- Build multi-stage: compilación del bundle de producción en una etapa, servido de estáticos en una etapa final ligera.
- Imagen base fijada explícitamente (sin `latest`).
- Configuración de variables de entorno de build resuelta vía `frontend/src/config/`.
