"""Add exchange rates and currency enum

Revision ID: 07284d443b62
Revises: c39777987217
Create Date: 2024-07-04 18:42:31.016595

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '07284d443b62'
down_revision: Union[str, None] = 'c39777987217'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()

    # Check if the enum type already exists
    enum_exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'currency')"
    )).scalar()

    if not enum_exists:
        # Create the Currency enum type only if it doesn't exist
        op.execute("CREATE TYPE currency AS ENUM ('RWF', 'USD', 'EUR', 'GBP')")

    # Check if the new_currency column already exists
    column_exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'project' AND column_name = 'new_currency')"
    )).scalar()

    if not column_exists:
        # Create a temporary column for the new currency enum
        op.add_column('project', sa.Column('new_currency', postgresql.ENUM('RWF', 'USD', 'EUR', 'GBP', name='currency', create_type=False), nullable=True))

    # Update the new_currency column based on the existing currency data
    op.execute("""
    UPDATE project
    SET new_currency = CASE
        WHEN lower(currency) LIKE '%usd%' OR lower(currency) LIKE '%us dollar%' THEN 'USD'::currency
        WHEN lower(currency) LIKE '%eur%' OR lower(currency) LIKE '%euro%' THEN 'EUR'::currency
        WHEN lower(currency) LIKE '%gbp%' OR lower(currency) LIKE '%pound%' THEN 'GBP'::currency
        WHEN lower(currency) LIKE '%rwf%' OR lower(currency) LIKE '%rwandan franc%' THEN 'RWF'::currency
        ELSE 'RWF'::currency  -- Default to RWF if no match
    END
    """)

    # Check if the old currency column exists before trying to drop it
    old_column_exists = connection.execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'project' AND column_name = 'currency')"
    )).scalar()

    if old_column_exists:
        # Drop the old currency column
        op.drop_column('project', 'currency')

    # Rename the new column
    op.alter_column('project', 'new_currency', new_column_name='currency', nullable=False)

    # Create the currency_exchange_rate table if it doesn't exist
    if not connection.dialect.has_table(connection, 'currency_exchange_rate'):
        op.create_table('currency_exchange_rate',
            sa.Column('uuid', sqlmodel.sql.sqltypes.GUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('deleted_status', sa.Boolean(), nullable=False),
            sa.Column('last_updated_at', sa.DateTime(), nullable=True),
            sa.Column('last_updated_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('deleted_by', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
            sa.Column('currency', postgresql.ENUM('RWF', 'USD', 'EUR', 'GBP', name='currency', create_type=False), nullable=False),
            sa.Column('rate', sa.Float(), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )

        # Create indexes
        op.create_index(op.f('ix_currency_exchange_rate_created_at'), 'currency_exchange_rate', ['created_at'], unique=False)
        op.create_index(op.f('ix_currency_exchange_rate_currency'), 'currency_exchange_rate', ['currency'], unique=False)
        op.create_index(op.f('ix_currency_exchange_rate_uuid'), 'currency_exchange_rate', ['uuid'], unique=True)


def downgrade() -> None:
    # Drop the currency_exchange_rate table and its indexes
    op.drop_index(op.f('ix_currency_exchange_rate_uuid'), table_name='currency_exchange_rate')
    op.drop_index(op.f('ix_currency_exchange_rate_currency'), table_name='currency_exchange_rate')
    op.drop_index(op.f('ix_currency_exchange_rate_created_at'), table_name='currency_exchange_rate')
    op.drop_table('currency_exchange_rate')

    # Revert the project table changes
    op.alter_column('project', 'currency', type_=sa.VARCHAR(), nullable=False)

    sa.Enum(name='currency').drop(op.get_bind())