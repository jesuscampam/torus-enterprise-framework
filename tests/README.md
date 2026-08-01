# tests/

Estrategia de pruebas del framework, en cumplimiento de los requisitos de testing definidos en [CODING-STANDARD.md](../docs/standards/CODING-STANDARD.md).

## Pirámide de pruebas

```
        ▲
       / \        e2e/            — pocos, cubren flujos críticos completos
      /---\
     /     \      integration/    — moderados, cubren la interacción entre capas
    /-------\
   /         \    unit/           — muchos, rápidos, cubren lógica aislada
  /-----------\
```

| Carpeta | Alcance |
|---|---|
| [`unit/`](unit/README.md) | Pruebas de una unidad aislada (`services/`, `repository/`, utilidades), con dependencias dobladas. |
| [`integration/`](integration/README.md) | Pruebas de la interacción real entre capas (por ejemplo, `services/` + `repository/` contra una base de datos de prueba). |
| [`e2e/`](e2e/README.md) | Pruebas de flujo completo a través de la API real, simulando el uso de un consumidor externo. |

## Principio rector

Cuanto más baja la capa en la pirámide, más pruebas y más rápidas deben ser; las pruebas e2e se reservan para los flujos de negocio más críticos, dado su mayor coste de mantenimiento y ejecución.
