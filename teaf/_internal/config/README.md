# config/

Configuración del backend por entorno, en cumplimiento del principio **Configuration by Environment**.

## Responsabilidad

- Definir clases de configuración tipadas (Pydantic Settings) que leen variables de entorno, con un perfil por entorno (`development`, `staging`, `production`).
- Centralizar la carga de secretos (credenciales de base de datos, claves JWT, credenciales de integraciones), delegando en un gestor de secretos en producción (Azure Key Vault).
- Exponer la configuración resuelta al resto de capas mediante inyección de dependencias (`core/`), nunca leyendo variables de entorno directamente desde `services/` o `api/`.

## Qué NO debe contener

- Valores de negocio hardcodeados.
- Secretos versionados en el repositorio (ver `.gitignore` en la raíz y [SECURITY-STANDARD.md](../../docs/standards/SECURITY-STANDARD.md)).

## Principio rector

Ningún valor que cambie entre entornos (Render, Azure staging, Azure producción) vive en el código; siempre se resuelve a través de esta capa.
