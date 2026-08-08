# RBAC y Políticas — TEAF

Autorización basada en roles (RBAC) más políticas arbitrarias, y los dos decoradores que las aplican a un endpoint. Ver [CLAIMS.md](CLAIMS.md) para `Principal`/`Role`/`Permission`.

## 1. El modelo

`Role`/`Permission` (`teaf._internal.providers.security.rbac`, Sprint 2.2, reutilizados sin duplicar) — `Permission` es un alias de `str` (el formato concreto, p. ej. `"users:delete"`, lo define cada aplicación); `Role` es un nombre + el conjunto de permisos que otorga:

```python
@dataclass(frozen=True, slots=True)
class Role:
    name: str
    permissions: frozenset[str] = frozenset()

    def grants(self, permission: str) -> bool: ...
```

## 2. Cómo se resuelve un `Principal`

```
Identity.claims.roles (nombres crudos, p. ej. del JWT o de grupos LDAP)
  │
  ▼  StaticRoleResolver — catálogo nombre -> Role
frozenset[Role]
  │
  ▼  RolePermissionResolver — unión de permisos directos + los que otorgan los roles
frozenset[Permission] (efectivos)
  │
  ▼
Principal(identity, roles, permissions, tenant_id)
```

`PrincipalResolver` combina ambos pasos — es lo que `SecurityMiddleware` invoca justo después de que un `IdentityProvider` autentica, antes de publicar el `SecurityContext`:

```python
from teaf.security import PrincipalResolver, StaticRoleResolver, Role

role_resolver = StaticRoleResolver(
    roles_by_name={"admin": Role(name="admin", permissions=frozenset({"users:delete"}))}
)
principal_resolver = PrincipalResolver(role_resolver=role_resolver)
```

Nombres de rol sin entrada en el catálogo se ignoran silenciosamente — una identidad puede traer roles que esta aplicación no reconoce (p. ej. un JWT emitido para varias aplicaciones distintas).

## 3. `Policy` — reglas que RBAC no puede expresar

```python
PolicyRule = Callable[[Principal], bool]

@dataclass(frozen=True, slots=True)
class Policy:
    name: str
    rule: PolicyRule
    description: str = ""
    def evaluate(self, principal: Principal) -> bool: ...
```

Sin DSL propio que aprender — `rule` es cualquier callable. Típicamente para reglas que dependen de un dato del propio `Principal` (tenant, combinación de claims) que un conjunto fijo de permisos no puede capturar:

```python
from teaf.security import Policy

same_tenant = Policy(name="same-tenant", rule=lambda p: p.tenant_id == "acme")
```

`DefaultPolicyEvaluator` (implementa el contrato `PolicyEvaluator`) solo delega en `policy.evaluate()` — la indirección permite sustituir la evaluación (logging, caché de resultados) sin tocar las políticas ya definidas ni los decoradores.

## 4. `@authorize()` — autorización declarativa por endpoint

```python
from teaf.security import authorize

@app.get("/admin-only")
@authorize()                              # solo exige autenticación
def admin_only(): ...

@app.get("/admin-only")
@authorize(role="admin")                  # o una lista: role=["admin", "editor"] (OR, no AND)
def admin_only(): ...

@app.get("/admin-only")
@authorize(permission="users:delete")
def admin_only(): ...

@app.get("/admin-only")
@authorize(policy=same_tenant)
def admin_only(): ...
```

Funciona tanto en endpoints síncronos como `async def` — envuelve la función original preservando su firma de cara a FastAPI (`functools.wraps` + `inspect.signature()`, que sigue `__wrapped__` automáticamente), así que `Depends(...)` en el endpoint decorado sigue funcionando sin cambios.

Lanza (401/403 automáticos, ver `teaf._internal.middleware.exception_handler`):

| Excepción | Cuándo | HTTP |
|---|---|---|
| `AuthenticationException` | No hay autenticación en absoluto. | 401 |
| `InsufficientPermissionException` | Autenticado, pero sin el rol/permiso exigido. | 403 |
| `PolicyViolationException` | Autenticado, pero la política no se satisface. | 403 |

## 5. `@allow_anonymous()` — marcador declarativo

```python
from teaf.security import allow_anonymous

@app.get("/status")
@allow_anonymous()
def status(): ...
```

**No-op en tiempo de ejecución**: `SecurityMiddleware` nunca bloquea una petición por falta de autenticación, así que un endpoint sin `@authorize()` ya es público. `@allow_anonymous()` existe para dejar esa intención explícita en el código — documentación ejecutable ("sí, este endpoint es público a propósito") — y como punto de extensión si una aplicación futura decide invertir la política por defecto.

## 6. Documentos relacionados

| Documento | Contenido |
|---|---|
| [CLAIMS.md](CLAIMS.md) | `Principal`/`Identity`/`Claims`/`SecurityContext` completos. |
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Flujo completo de una petición, incluyendo dónde encaja RBAC. |
| [`examples/role-based-endpoint/`](../../examples/role-based-endpoint/), [`examples/permission-based-endpoint/`](../../examples/permission-based-endpoint/), [`examples/policy-based-endpoint/`](../../examples/policy-based-endpoint/), [`examples/anonymous-endpoint/`](../../examples/anonymous-endpoint/) | Los cuatro decoradores, ejecutables. |
