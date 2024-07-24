"""Project: fiscal years and budget array

Revision ID: 94ada9ff040c
Revises: 621df8d701b9
Create Date: 2024-07-24 23:03:46.997994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '94ada9ff040c'
down_revision: Union[str, None] = '621df8d701b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add new columns
    op.add_column('project', sa.Column('new_budget', postgresql.ARRAY(sa.Float()), nullable=True))
    op.add_column('project', sa.Column('fiscal_years', postgresql.ARRAY(sa.String()), nullable=True))

    # Step 2: Migrate existing data
    op.execute("""
    UPDATE project
    SET new_budget = ARRAY[budget],
        fiscal_years = ARRAY['2024/2025']
    """)

    # Step 3: Drop old column and rename new column
    op.drop_column('project', 'budget')
    op.alter_column('project', 'new_budget', new_column_name='budget')

    # Step 4: Set new columns to not nullable
    op.alter_column('project', 'budget', nullable=False)
    op.alter_column('project', 'fiscal_years', nullable=False)

    # Step 5: Drop the currency column as per auto-generated migration
    op.drop_column('project', 'currency')


def downgrade() -> None:
    # Step 1: Add back the currency column
    op.add_column('project', sa.Column('currency', postgresql.ENUM('RWF', 'USD', 'EUR', 'GBP', name='currency', create_type=False), autoincrement=False, nullable=False))

    # Step 2: Convert back to single budget value (taking the first element of the array)
    op.execute("""
    ALTER TABLE project
    ADD COLUMN old_budget FLOAT
    """)

    op.execute("""
    UPDATE project
    SET old_budget = budget[1]
    """)

    # Step 3: Drop new columns and rename old_budget back to budget
    op.drop_column('project', 'budget')
    op.drop_column('project', 'fiscal_years')
    op.alter_column('project', 'old_budget', new_column_name='budget')

    # Step 4: Ensure budget is not nullable
    op.alter_column('project', 'budget', nullable=False)
