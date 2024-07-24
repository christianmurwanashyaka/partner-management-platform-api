"""Project: add back currency column

Revision ID: 973c0200f7a3
Revises: 94ada9ff040c
Create Date: 2024-07-24 23:15:26.204241

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '973c0200f7a3'
down_revision: Union[str, None] = '94ada9ff040c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add back the currency column
    op.add_column('project', sa.Column('currency', postgresql.ENUM('RWF', 'USD', 'EUR', 'GBP', name='currency'), nullable=False, server_default='RWF'))


def downgrade() -> None:
    # Remove the currency column if we need to roll back
    op.drop_column('project', 'currency')