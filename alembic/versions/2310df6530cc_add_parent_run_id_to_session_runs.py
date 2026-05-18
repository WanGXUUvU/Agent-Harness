"""add parent_run_id to session_runs

Revision ID: 2310df6530cc
Revises: 9b0c8cf96dcd
Create Date: 2026-05-17 15:38:00.236733

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2310df6530cc'
down_revision: Union[str, Sequence[str], None] = '9b0c8cf96dcd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('session_runs', sa.Column('parent_run_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_session_runs_parent_run_id'), 'session_runs', ['parent_run_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_session_runs_parent_run_id'), table_name='session_runs')
    op.drop_column('session_runs', 'parent_run_id')
