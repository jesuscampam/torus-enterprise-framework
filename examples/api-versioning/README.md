# api-versioning/

Las tres estrategias de versionado de `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)), la versión por defecto y la deprecación.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- **URI** (`/api/v2/orders`) es la más visible y la más fácil de enrutar en un balanceador, a costa de ensuciar la URL del recurso.
- **Cabecera** (`X-API-Version: 2`) mantiene la URL limpia, pero es invisible desde un navegador.
- **Tipo de medio** (`Accept: application/vnd.teaf.v2+json`) es la más fiel a HTTP y la más incómoda de escribir a mano.
- Ninguna es "la correcta": las tres están implementadas y el orden de prioridad se declara en `ApiVersioningPolicy.strategies` — ver [VERSIONING.md](../../docs/api/VERSIONING.md).
- Una versión obsoleta viaja con `Deprecation: true` y `Sunset: <fecha>`, la forma estándar de avisar de una retirada sin romper a nadie todavía.
- Con `strict=True` (por defecto) una versión desconocida es un `400` explícito: servir la v1 a quien pidió la v3 produce errores mucho más difíciles de diagnosticar.
- El middleware **no enruta** por versión: deja el resultado en `request.state.api_version` y es la aplicación quien decide qué implementación responde.
