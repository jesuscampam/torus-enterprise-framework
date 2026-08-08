# health-checks/

`/health`/`/ready` evaluando de verdad el `ModuleHealth` de cada módulo bootstrapeado, vía `CompositeHealthChecker` (Sprint 2.8, ADR-008) — sin construir el checker a mano, `Application` ya lo conecta.

## Ejecutar

```bash
pip install -e ../../..
python main.py
```

## Qué observar

- `PaymentsGatewayModule` declara un `ModuleHealth` que siempre resuelve `Health.HEALTHY`; `ShippingProviderModule` resuelve `Health.DEGRADED` — cada uno vía `ModuleBuilder.add_healthcheck(name=..., check=...)`, igual que [`basic-module/`](../basic-module/).
- `GET /health` agrega ambos: el desglose (`modules.checks`) muestra cada check por separado (`payments.payments.ping`, `shipping.shipping.ping` — prefijados por el id del módulo), y el estado global (`modules.status`) es el peor de los dos (`degraded`).
- `GET /ready` devuelve `200`/`"ready"` mientras nada esté `UNHEALTHY` — un módulo `DEGRADED` no bloquea el tráfico (sigue respondiendo, solo peor); solo `UNHEALTHY` hace que `/ready` devuelva `503`.
- `/live` (no usado en este ejemplo) nunca evalúa dependencias a propósito — solo confirma que el proceso responde, para no provocar reinicios en cascada cuando una dependencia externa está caída pero el proceso sigue sano.
