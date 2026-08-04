# security/

Autenticación, autorización y criptografía del framework, en cumplimiento de [SECURITY-STANDARD.md](../../docs/standards/SECURITY-STANDARD.md).

## Responsabilidad

- Emisión y verificación de tokens **JWT** (access y refresh).
- Modelo de autorización **RBAC**: verificación de roles y permisos.
- Hashing y verificación de contraseñas (bcrypt/argon2).
- Políticas de permisos reutilizables, invocadas desde `api/` o `services/` según el nivel de granularidad requerido.

## Qué NO debe contener

- Lógica de negocio no relacionada con seguridad.
- Reglas de autorización de un dominio específico hardcodeadas de forma ad-hoc fuera del modelo RBAC centralizado.

## Principio rector

Toda decisión de "quién puede hacer qué" pasa por esta capa; ninguna otra capa implementa su propia lógica de autorización paralela.
