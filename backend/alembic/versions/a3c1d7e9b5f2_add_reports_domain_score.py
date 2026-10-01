"""add reports.domain_score

Revision ID: a3c1d7e9b5f2
Revises: 82d336408f7b
Create Date: 2026-10-01 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c1d7e9b5f2'
down_revision: Union[str, Sequence[str], None] = '82d336408f7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('reports', sa.Column('domain_score', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('reports', 'domain_score')
