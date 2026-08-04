# module-registration/

Registra un módulo (`HelloModule`) usando exclusivamente la Module Registration API de `teaf.Application` (Sprint 2.6.3) — sin `bootstrap()` manual, sin `asyncio.run()`, sin threads, sin conocer el `Runtime`.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Application(modules=[HelloModule()])` es la única línea que "registra" el módulo — nada más lo toca.
- El módulo arranca automáticamente cuando arranca el ciclo de vida ASGI de la aplicación (aquí, al entrar en `with TestClient(app.asgi):` — en producción, al servir con `uvicorn app:app`).
- Existe una forma encadenable equivalente: `Application().add_module(HelloModule())` (comentada en `main.py`).
- Tras el `with`, `app.runtime.modules` y `app.runtime.capability_registry` ya reflejan el módulo — se registró, enlazó sus capacidades y llegó a `READY` sin que este archivo llamara a ningún método interno del Runtime.
