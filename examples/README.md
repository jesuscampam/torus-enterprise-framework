# examples/

Ejemplos mínimos de la API pública de TEAF (`teaf/`, ver [docs/public-api/](../docs/public-api/)). Cada uno importa **exclusivamente** `from teaf import ...` — ninguno conoce `teaf/_internal/` (ver [IMPORT-GUIDE.md](../docs/public-api/IMPORT-GUIDE.md)). Verificado automáticamente por `scripts/check_public_api_boundary.py` y por `tests/unit/test_import_boundary_checker.py`.

## Requisito previo

```bash
pip install -e .
```

## Ejemplos

| Carpeta | Qué demuestra | Ejecutar |
|---|---|---|
| [`hello-world/`](hello-world/) | Lo mínimo: construir una `Application`, arrancar y apagar su `Runtime`. | `python examples/hello-world/main.py` |
| [`basic-module/`](basic-module/) | Construir un módulo propio con `Module`/`ModuleBuilder` y registrarlo contra un `Runtime`. | `python examples/basic-module/main.py` |
| [`application-bootstrap/`](application-bootstrap/) | Una `Application` completa con un módulo propio ya registrado, más introspección del `Runtime`. | `python examples/application-bootstrap/main.py` |
| [`module-registration/`](module-registration/) | Registrar un módulo con la Module Registration API (`Application(modules=[...])`) — sin `bootstrap()` manual, sin `asyncio.run()`, sin threads. | `python examples/module-registration/main.py` |

Progresión sugerida: léelos en ese orden — cada uno añade una pieza sobre el anterior.
