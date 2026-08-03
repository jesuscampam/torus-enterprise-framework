"""baseline: infraestructura sin tablas de negocio

Revision ID: e5ee0f589cca
Revises: 
Create Date: 2026-08-03 17:59:48.180087

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "e5ee0f589cca"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
