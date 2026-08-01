# docker/

Estrategia de contenerización del framework, en cumplimiento del principio **Docker First** (ver [ADR-003](../docs/architecture/adr/ADR-003-uso-de-docker.md)).

## Contenido previsto

| Carpeta | Responsabilidad |
|---|---|
| [`backend/`](backend/README.md) | Dockerfile del backend (FastAPI). |
| [`frontend/`](frontend/README.md) | Dockerfile del frontend (React). |

## Estado actual

Esta iteración solo define la estructura de carpetas. Los `Dockerfile` de cada componente y los archivos `docker-compose.yml` (orquestación local de backend + PostgreSQL) se incorporan en la Versión 1 del [roadmap](../docs/roadmap/ROADMAP.md), junto con el pipeline de build de imágenes en `.github/workflows/`.

## Principio rector

Las mismas imágenes construidas y probadas en CI son las que se despliegan en Render (POC) y Azure App Service (producción) — sin reconstrucción ni configuración distinta entre entornos más allá de variables de entorno resueltas vía `backend/config/` y `frontend/src/config/`.
