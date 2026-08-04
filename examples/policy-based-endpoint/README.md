# policy-based-endpoint/

Proteger un endpoint con `@authorize(policy=...)` — una regla arbitraria sobre el `Principal` (aquí, pertenencia a un tenant), más expresiva que un rol o permiso plano.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- `Policy(name=..., rule=lambda principal: ...)` es solo un callable — sin un DSL propio que aprender.
- Un usuario del tenant `"acme"` puede acceder a `/tenants/acme/settings`; uno del tenant `"globex"` recibe `403`, aunque ambos estén autenticados con el mismo mecanismo (JWT).
- `DefaultPolicyEvaluator` (usado internamente por `@authorize(policy=...)`) solo delega en `policy.evaluate(principal)` — la indirección existe para poder sustituir la evaluación (logging, caché) sin tocar las políticas ya definidas.
