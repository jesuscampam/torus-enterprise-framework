# permission-based-endpoint/

Proteger un endpoint con `@authorize(permission="invoices:void")` — dos roles distintos otorgan el mismo permiso, y el endpoint acepta a cualquiera de los dos sin conocer sus nombres.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- El rol `"support"` (que solo tiene `invoices:read`) recibe `403` en `/invoices/{id}/void`; el rol `"billing-operator"` (que sí tiene `invoices:void`) recibe `200`.
- A diferencia de `@authorize(role=...)`, un chequeo por permiso desacopla el endpoint del nombre exacto del rol — cualquier rol futuro que otorgue `"invoices:void"` funcionaría sin tocar el endpoint.
- `RolePermissionResolver` (usado internamente por `PrincipalResolver`) calcula los permisos efectivos como la unión de los permisos directos del principal y los que otorgan sus roles.
