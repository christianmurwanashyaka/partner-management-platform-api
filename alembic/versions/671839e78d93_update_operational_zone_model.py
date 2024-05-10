"""Update operational zone model

Revision ID: 671839e78d93
Revises: 3a4f795df854
Create Date: 2024-05-08 22:56:11.179618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlmodel

# revision identifiers, used by Alembic.
revision: str = '671839e78d93'
down_revision: Union[str, None] = '3a4f795df854'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('operational_zone', sa.Column('district', sa.String(), nullable=True))
    op.execute('''
    UPDATE operational_zone
    SET district = CASE WHEN cardinality(districts) > 0 THEN districts[1] ELSE NULL END
    ''')
    op.drop_column('operational_zone', 'districts')
    op.alter_column('operational_zone', 'district', nullable=False)


def downgrade():
    op.add_column('operational_zone', sa.Column('districts', postgresql.ARRAY(sa.String()), nullable=True))
    op.execute('''
    UPDATE operational_zone
    SET districts = ARRAY[CAST(district AS VARCHAR)]
    ''')
    op.drop_column('operational_zone', 'district')