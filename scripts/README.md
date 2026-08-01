# scripts/

Scripts de automatización operativa del framework, fuera del código de aplicación.

## Alcance previsto (a partir de la Versión 1)

- Scripts de bootstrap de entorno local (`setup.sh`): instalación de dependencias, levantamiento de contenedores, aplicación de migraciones y seeds.
- Scripts de calidad de código: ejecución conjunta de lint/format/type-check para backend y frontend.
- Scripts de utilidad para migraciones (generación y aplicación de revisiones Alembic).
- Scripts de apoyo al despliegue (invocados desde los workflows de `.github/workflows/`), nunca lógica de despliegue duplicada fuera de CI.

## Principio rector

Todo script de esta carpeta debe ser idempotente y seguro de ejecutar repetidamente; ninguno debe requerir pasos manuales no documentados.

## Estado actual

Solo esta documentación; los scripts concretos se incorporan junto con el bootstrap ejecutable de la Versión 1 (ver [roadmap](../docs/roadmap/ROADMAP.md)).
