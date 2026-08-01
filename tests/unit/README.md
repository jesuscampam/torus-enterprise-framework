# unit/

Pruebas unitarias: verifican una única unidad de código en aislamiento (una función, un método, un caso de uso de `services/`), con todas sus dependencias externas dobladas (mocks/fakes).

## Convenciones

- Cada prueba unitaria debe ejecutarse sin red, sin base de datos real y sin sistema de archivos.
- La estructura de `tests/unit/` refleja la estructura de `backend/` (por ejemplo, pruebas de `backend/services/` viven en `tests/unit/services/`).
- Cobertura mínima objetivo para `services/` y `repository/`: 80% (ver [CODING-STANDARD.md](../../docs/standards/CODING-STANDARD.md)).
