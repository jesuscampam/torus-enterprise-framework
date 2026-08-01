# Plantilla — Migración Alembic (`database/migrations/`)

> PLANTILLA — no ejecutable, no forma parte de la aplicación. Código ilustrativo para copiar al implementar una migración real, conforme a [DATABASE-STANDARD.md](../docs/standards/DATABASE-STANDARD.md).

## Cómo usar esta plantilla

1. Genera la migración con `alembic revision --autogenerate -m "descripción"` y **revisa manualmente** el resultado — Alembic no detecta de forma fiable renombrados ni ciertos cambios de tipo.
2. Toda migración debe ser reversible (`downgrade()` implementado), salvo que la irreversibilidad sea intencional y esté documentada.
3. Toda tabla nueva incluye `id UUID` como PK y las columnas de auditoría obligatorias (`created_at`, `updated_at`, `deleted_at`).

```python
# database/migrations/versions/{{timestamp}}_{{descripcion_corta}}.py
#
# Migración: {{descripción de qué cambia y por qué}}

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, usados por Alembic
revision = "{{revision_id}}"
down_revision = "{{revision_anterior_id}}"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "{{tabla}}",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        # TODO al implementar: columnas propias del dominio
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # TODO al implementar: índices explícitos sobre claves foráneas y columnas de filtro frecuente
    # op.create_index("ix_{{tabla}}_{{columna}}", "{{tabla}}", ["{{columna}}"])


def downgrade() -> None:
    op.drop_table("{{tabla}}")
```

## Qué NO hacer en este archivo

- No modificar el esquema de producción manualmente fuera de una migración versionada.
- No aplicar una migración irreversible sin documentar explícitamente el motivo en el mensaje de la revisión.
- No omitir los índices de claves foráneas.
