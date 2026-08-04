# LDAP / Active Directory — TEAF

`LDAPProvider` — bind con usuario/contraseña contra LDAP/Active Directory vía `ldap3`, búsqueda de sus grupos, y conversión de grupos a roles/permisos.

## 1. Configuración

```python
from teaf.security import LDAPProvider

ldap_provider = LDAPProvider(
    server_uri="ldaps://corp.example.com",
    base_dn="dc=corp,dc=example,dc=com",
    user_dn_template="cn={username},{base_dn}",   # o "{username}@corp.example.com" para bind por UPN (Active Directory)
    group_search_base=None,                         # por defecto, base_dn
    group_search_filter="(member={user_dn})",
    group_to_role={"network-admins": "admin"},         # cn de grupo LDAP -> nombre de rol
    group_to_permissions={"network-admins": frozenset({"tickets:close"})},   # cn de grupo -> permisos directos
    use_ssl=True,
)
```

`user_dn_template` acepta los placeholders `{username}`/`{base_dn}`. `group_to_role`/`group_to_permissions` son opcionales y combinables — un grupo puede otorgar un rol, permisos directos, o ambos.

## 2. Cómo autentica

```
Authorization: Basic <base64(username:password)>
  │
  ▼  SecurityMiddleware decodifica y enruta al scheme "ldap"
LDAPProvider.authenticate()
  │  1. Bind simple: user_dn + password (nunca se guarda ni reenvía la contraseña más allá del bind)
  │  2. Búsqueda de grupos del usuario (group_search_base + group_search_filter)
  │  3. Conversión de cada grupo a rol/permisos según group_to_role/group_to_permissions
  ▼
Identity(id=username, provider_id="ldap", claims=Claims(sub=username, roles=..., permissions=..., groups=...))
```

`ldap3` es síncrono — cada bind/búsqueda corre en threadpool (`asyncio.to_thread`) para no bloquear el event loop (ver [ADR-007](../architecture/adr/ADR-007-enterprise-security-stack.md)).

## 3. Conectarlo

```python
from teaf.security import IdentityProviderRegistry, AnonymousIdentityProvider

provider_registry = IdentityProviderRegistry([AnonymousIdentityProvider(), ldap_provider])
```

Un cliente HTTP envía `Authorization: Basic <base64(usuario:contraseña)>` — `SecurityMiddleware` lo decodifica y enruta automáticamente al scheme `"ldap"`.

## 4. Probarlo sin un servidor LDAP real

`LDAPProvider(connection_factory=...)` acepta cualquier callable con la firma de `ldap3.Connection` — el valor por defecto (`ldap3.Connection`) habla con `server_uri` de verdad; para pruebas o demos se puede inyectar un sustituto:

```python
class FakeLdapConnection:
    def __init__(self, server, user, password, auto_bind): ...   # levanta LDAPBindError si las credenciales son inválidas
    def search(self, base, search_filter, attributes): ...
    def unbind(self): ...

ldap_provider = LDAPProvider(..., connection_factory=FakeLdapConnection)
```

Ver [`examples/ldap-login/`](../../examples/ldap-login/) para un ejemplo completo y ejecutable con este patrón, y `tests/unit/test_security_identity_providers.py` para el caso de prueba equivalente con `ldap3`'s `MOCK_SYNC` descartado a favor de este enfoque (ver la nota de diseño en ese archivo de test sobre por qué `MOCK_SYNC` no sirve aquí).

## 5. Documentos relacionados

| Documento | Contenido |
|---|---|
| [SECURITY-ARCHITECTURE.md](SECURITY-ARCHITECTURE.md) | Flujo completo de una petición, incluyendo el "sniffing" de `Authorization: Basic`. |
| [RBAC.md](RBAC.md) | Cómo los roles resultantes (`group_to_role`) se combinan con permisos en un `Principal`. |
