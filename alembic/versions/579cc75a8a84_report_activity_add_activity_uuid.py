"""Report Activity: add activity uuid

Revision ID: 579cc75a8a84
Revises: 53a12e716407
Create Date: 2024-09-25 23:14:28.459394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision: str = '579cc75a8a84'
down_revision: Union[str, None] = '53a12e716407'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add the new column as nullable
    op.add_column('report_activity', sa.Column('activity_uuid', sqlmodel.sql.sqltypes.GUID(), nullable=True))
    op.create_index(op.f('ix_report_activity_activity_uuid'), 'report_activity', ['activity_uuid'], unique=False)

    # Step 2: Update existing records
    # Create a connection
    connection = op.get_bind()

    # Define tables for the SQL expression
    report_activity = table('report_activity',
        column('uuid', sa.UUID),
        column('report_uuid', sa.UUID),
        column('activity_uuid', sa.UUID)
    )
    activity = table('activity',
        column('uuid', sa.UUID),
        column('report_uuid', sa.UUID)
    )

    # Update statement
    update_stmt = report_activity.update().values(
        activity_uuid=activity.c.uuid
    ).where(
        report_activity.c.report_uuid == activity.c.report_uuid
    )

    # Execute the update
    connection.execute(update_stmt)

    # Step 3: Set the column to NOT NULL
    op.alter_column('report_activity', 'activity_uuid', nullable=False)

    # Step 4: Add the foreign key constraint
    op.create_foreign_key(None, 'report_activity', 'activity', ['activity_uuid'], ['uuid'])


def downgrade() -> None:
    op.drop_constraint(None, 'report_activity', type_='foreignkey')
    op.drop_index(op.f('ix_report_activity_activity_uuid'), table_name='report_activity')
    op.drop_column('report_activity', 'activity_uuid')
    # Note: The operations for dropping user_activity and user_domain tables are removed
    # as they seem unrelated to this specific migration.