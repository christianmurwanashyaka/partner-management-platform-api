"""Change user role to moh staff

Revision ID: a4ab4270f268
Revises: a64940c1c4bb
Create Date: 2024-05-18 20:21:07.081247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a4ab4270f268'
down_revision: Union[str, None] = 'a64940c1c4bb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the new enum type
    new_enum = sa.Enum(
        'PARTNER_COORDINATOR', 'TECHNICAL_DEPARTMENT', 'LEGAL_ADVISOR', 'HOD', 'PS', 'MINISTER_OF_STATE', 'MINISTER',
        name='mohstafflevel'
    )
    new_enum.create(op.get_bind(), checkfirst=True)

    # Alter the column to use the new enum type, using explicit cast
    op.execute('ALTER TABLE "user" ALTER COLUMN level TYPE mohstafflevel USING level::text::mohstafflevel')

    # Drop the old enum type
    op.execute('DROP TYPE swapteamlevel')


def downgrade() -> None:
    # Create the old enum type
    old_enum = postgresql.ENUM(
        'PARTNER_COORDINATOR', 'TECHNICAL_DEPARTMENT', 'LEGAL_ADVISOR', 'HOD', 'PS', 'MINISTER_OF_STATE', 'MINISTER',
        name='swapteamlevel'
    )
    old_enum.create(op.get_bind(), checkfirst=True)

    # Alter the column to use the old enum type, using explicit cast
    op.execute('ALTER TABLE "user" ALTER COLUMN level TYPE swapteamlevel USING level::text::swapteamlevel')

    # Drop the new enum type
    op.execute('DROP TYPE mohstafflevel')
