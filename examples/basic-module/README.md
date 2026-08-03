# basic-module/

Construye un módulo TEAF propio (`GreeterModule`) heredando de `teaf.Module` y lo registra contra un `teaf.Runtime` real — un servicio, una capacidad y un healthcheck, sin tocar `backend/`.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Module` es el mismo objeto que `ModuleBase` — alias corto para heredar de él (ver [PUBLIC-API.md](../../docs/public-api/PUBLIC-API.md)).
- `get_manifest()` es la única pieza obligatoria de un módulo — describe qué aporta, nunca registra nada por sí misma.
- `await module.bootstrap(context)` valida el manifiesto, registra el servicio (`ServiceContainer`) y la capacidad (`CapabilityRegistry`) automáticamente — el módulo nunca llama a esos registros a mano.
- `runtime.resolve_service(Greeter)` resuelve el servicio ya registrado, por su contrato (`Greeter`), sin que el llamador conozca la factory que lo construyó.
