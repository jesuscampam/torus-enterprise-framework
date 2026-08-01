# docker/backend/

Ubicación reservada para el `Dockerfile` del backend (FastAPI).

## Alcance previsto (Versión 1)

- Build multi-stage: etapa de instalación de dependencias separada de la etapa de ejecución, para minimizar el tamaño final de la imagen.
- Imagen base oficial de Python, versión fijada explícitamente (sin `latest`).
- Ejecución como usuario no privilegiado dentro del contenedor (alineado con [SECURITY-STANDARD.md](../../docs/standards/SECURITY-STANDARD.md)).
