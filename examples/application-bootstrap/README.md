# application-bootstrap/

El ejemplo más completo: una `teaf.Application` real (la misma fachada que serviría un `uvicorn` en producción) con un módulo propio (`ClockModule`) registrado sobre su `Runtime`, más introspección del estado resultante.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Application()` ya trae su propio `Runtime` (`app.runtime`) — no hace falta construir uno aparte, a diferencia de [`basic-module/`](../basic-module/).
- Un módulo propio se registra sobre `app.runtime` exactamente igual que sobre cualquier otro `Runtime` — `Application` no añade ninguna API distinta para esto.
- `app.runtime.diagnostics()` expone el estado operativo (módulos/servicios/capacidades registrados) sin necesidad de una petición HTTP — la misma información que sirve `GET /runtime/info` cuando la aplicación corre como servidor real.
