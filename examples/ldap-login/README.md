# ldap-login/

Autenticación contra LDAP/Active Directory (`LDAPProvider`): bind con usuario/contraseña vía `Authorization: Basic`, búsqueda de grupos y su conversión a roles.

## Ejecutar

```bash
pip install -e ../../..   # o: pip install -e . desde la raíz del repositorio
python main.py
```

## Qué observar

- El ejemplo usa un servidor LDAP falso (`connection_factory`) para poder ejecutarse sin un Active Directory real disponible — en producción se omite ese parámetro y `LDAPProvider` habla con `server_uri` de verdad vía `ldap3.Connection`.
- `group_to_role={"network-admins": "admin"}` es lo único que traduce un grupo LDAP crudo a un rol de la aplicación — `LDAPProvider` no conoce el vocabulario de roles de ninguna aplicación concreta.
- Un bind fallido (contraseña incorrecta) nunca revela si el usuario existe — cae a anónimo igual que cualquier otro fallo de autenticación.
- `SecurityMiddleware` enruta automáticamente `Authorization: Basic ...` hacia el proveedor `"ldap"` — ver el "sniffing" de credenciales en `docs/security/SECURITY-ARCHITECTURE.md`.
