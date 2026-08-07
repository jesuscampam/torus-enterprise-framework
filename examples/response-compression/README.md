# response-compression/

Compresión de respuestas en `teaf.api` (Sprint 2.9, [ADR-009](../../docs/architecture/adr/ADR-009-enterprise-api-protection.md)): GZip sobre la librería estándar y Brotli sobre un paquete opcional.

## Ejecutar

```bash
pip install -e ../../..
python main.py

# opcional, para ver Brotli en acción:
pip install brotli
```

## Qué observar

- **GZip está siempre disponible** (`gzip` de la librería estándar). **Brotli requiere `pip install brotli`** (o `brotlicffi`): no es una dependencia dura del framework porque añadirla exigiría su propio ADR ([STACK.md](../../docs/architecture/STACK.md), [CLAUDE.md](../../CLAUDE.md) §4). Si falta, `available` es `False` y el negociador simplemente no lo elige — la respuesta sale en GZip o sin comprimir, nunca falla.
- La preferencia del **cliente** (`Accept-Encoding`, con sus factores `q`) manda sobre el orden del servidor, que es lo que exige HTTP.
- Por debajo de `minimum_size_bytes` no se comprime: comprimir 200 bytes cuesta más CPU de la que ahorra en red, y las ~20 bytes de cabecera del propio formato se comen el ahorro.
- Solo se comprimen tipos que se benefician (texto, JSON, XML, SVG): un JPEG o un ZIP ya vienen comprimidos y volver a hacerlo los agranda.
- Si el resultado comprimido **no** es más pequeño que el original, se devuelve el original.
- `Vary: Accept-Encoding` va siempre: sin él, una caché podría servir la respuesta comprimida a un cliente que no la admite.
