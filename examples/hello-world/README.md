# hello-world/

El ejemplo más pequeño posible: construir una `teaf.Application`, arrancar su `Runtime` y apagarlo. Sin módulos propios, sin servidor HTTP real — solo el ciclo de vida.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Application()` construye la aplicación (configuración, logging, `Runtime`) sin arrancarla todavía.
- `await app.runtime.startup()` / `await app.runtime.shutdown()` — el mismo ciclo de vida que dispara un servidor ASGI real (`uvicorn`) automáticamente vía `lifespan`; aquí se dispara a mano porque no hay servidor.
- `app.version` — la versión de TEAF con la que se construyó esta instancia (`teaf.Version.framework`, ver [VERSIONING.md](../../docs/public-api/VERSIONING.md)).
