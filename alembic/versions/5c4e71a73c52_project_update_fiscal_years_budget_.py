"""Project: update fiscal years, budget, total budget, funding source

Revision ID: 5c4e71a73c52
Revises: 
Create Date: 2024-07-25 11:13:39.483140

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5c4e71a73c52'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create a temporary table to store the old data
    op.create_table('temp_project',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('budget', postgresql.ARRAY(sa.Float()), nullable=True),
        sa.Column('fiscal_years', postgresql.ARRAY(sa.String()), nullable=True),
        sa.PrimaryKeyConstraint('uuid')
    )

    # Copy data from the project table to the temporary table
    op.execute(
        "INSERT INTO temp_project (uuid, budget, fiscal_years) "
        "SELECT uuid, budget, fiscal_years FROM project"
    )

    # Add new columns
    op.add_column('project', sa.Column('fiscal_year_budgets', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('project', sa.Column('total_budget', sa.Float(), nullable=True))

    # Update the project table with the new structure
    op.execute(
        "UPDATE project "
        "SET fiscal_year_budgets = jsonb_build_array(jsonb_build_object('fiscal_year', temp_project.fiscal_years[1], 'budget', temp_project.budget[1])), "
        "    total_budget = temp_project.budget[1] "
        "FROM temp_project "
        "WHERE project.uuid = temp_project.uuid"
    )

    # Drop old columns
    op.drop_column('project', 'budget')
    op.drop_column('project', 'fiscal_years')

    # Drop the temporary table
    op.drop_table('temp_project')

    # Make the new columns non-nullable
    op.alter_column('project', 'fiscal_year_budgets', nullable=False)
    op.alter_column('project', 'total_budget', nullable=False)

def downgrade():
    # Create a temporary table to store the new data
    op.create_table('temp_project',
        sa.Column('uuid', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('fiscal_year_budgets', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('total_budget', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('uuid')
    )

    # Copy data from the project table to the temporary table
    op.execute(
        "INSERT INTO temp_project (uuid, fiscal_year_budgets, total_budget) "
        "SELECT uuid, fiscal_year_budgets, total_budget FROM project"
    )

    # Add old columns back
    op.add_column('project', sa.Column('budget', postgresql.ARRAY(sa.Float()), nullable=True))
    op.add_column('project', sa.Column('fiscal_years', postgresql.ARRAY(sa.String()), nullable=True))

    # Update the project table with the old structure
    op.execute(
        "UPDATE project "
        "SET budget = ARRAY[(temp_project.fiscal_year_budgets->0->>'budget')::float], "
        "    fiscal_years = ARRAY[temp_project.fiscal_year_budgets->0->>'fiscal_year'] "
        "FROM temp_project "
        "WHERE project.uuid = temp_project.uuid"
    )

    # Drop new columns
    op.drop_column('project', 'fiscal_year_budgets')
    op.drop_column('project', 'total_budget')

    # Drop the temporary table
    op.drop_table('temp_project')

    # Make the old columns non-nullable
    op.alter_column('project', 'budget', nullable=False)
    op.alter_column('project', 'fiscal_years', nullable=False)