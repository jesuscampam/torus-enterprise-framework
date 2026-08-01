# Plantilla — Router de API (`backend/api/`)

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Código ilustrativo para copiar al implementar un endpoint real, conforme a [API-STANDARD.md](../docs/standards/API-STANDARD.md).

## Cómo usar esta plantilla

1. Reemplaza `{{Recurso}}` / `{{recurso}}` por el nombre del recurso (por ejemplo, `Incident` / `incidents`).
2. El router **nunca** contiene lógica de negocio: solo valida con `schemas/`, invoca `services/` y traduce el resultado a una respuesta HTTP.
3. Todo endpoint debe declarar sus posibles errores en formato RFC 7807 (ver `API-STANDARD.md`, sección 6).

```python
# backend/api/v1/{{recurso}}/router.py
#
# Router de ejemplo para el recurso "{{Recurso}}".
# Sigue API-STANDARD.md: versionado /api/v1, envelope de colecciones,
# paginación estándar, errores RFC 7807.

from fastapi import APIRouter, Depends, status

from backend.core.dependencies import get_{{recurso}}_service  # inyección de dependencias (core/)
from backend.schemas.{{recurso}} import (
    {{Recurso}}CreateSchema,
    {{Recurso}}ResponseSchema,
    {{Recurso}}ListResponseSchema,
)
from backend.services.{{recurso}}_service import {{Recurso}}Service

router = APIRouter(prefix="/api/v1/{{recurso}}s", tags=["{{Recurso}}"])


@router.get("", response_model={{Recurso}}ListResponseSchema, status_code=status.HTTP_200_OK)
async def list_{{recurso}}s(
    page: int = 1,
    page_size: int = 20,
    service: {{Recurso}}Service = Depends(get_{{recurso}}_service),
) -> {{Recurso}}ListResponseSchema:
    """Lista paginada de {{recurso}}s. La paginación sigue API-STANDARD.md, sección 5."""
    # El router SOLO orquesta: la lógica real vive en el service.
    return await service.list_paginated(page=page, page_size=page_size)


@router.post("", response_model={{Recurso}}ResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_{{recurso}}(
    payload: {{Recurso}}CreateSchema,
    service: {{Recurso}}Service = Depends(get_{{recurso}}_service),
) -> {{Recurso}}ResponseSchema:
    """Crea un {{recurso}} nuevo. `payload` ya viene validado por el schema."""
    return await service.create(payload)


# TODO al implementar: GET /{id}, PUT /{id}, PATCH /{id}, DELETE /{id}
# TODO al implementar: documentar cada código de error posible (401/403/404/409/422)
# TODO al implementar: proteger la ruta con la dependencia de autenticación de backend/security/
```

## Qué NO hacer en este archivo

- No importar `backend/models/` ni `backend/database/` directamente.
- No escribir reglas de negocio aquí (pertenecen a `{{Recurso}}Service`).
- No devolver un `model` de SQLAlchemy como respuesta; siempre un `schema`.
