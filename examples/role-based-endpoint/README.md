# role-based-endpoint/

Proteger un endpoint con `@authorize(role="admin")` — RBAC clásico: un catálogo de roles (`StaticRoleResolver`) resuelve los nombres de rol de un JWT a objetos `Role`.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- Un usuario con el rol `"support"` recibe `403` en `/incidents/{id}/close`; uno con `"admin"` recibe `200`.
- `@authorize(role="admin")` también acepta una lista (`role=["admin", "editor"]`) — basta con tener alguno de los roles indicados.
- El catálogo de roles (`StaticRoleResolver`) vive en la aplicación, no en el `IdentityProvider` — el mismo JWT funcionaría igual si el catálogo cambiara.
