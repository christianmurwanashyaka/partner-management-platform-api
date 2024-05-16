"""Add mou review decision

Revision ID: a64940c1c4bb
Revises: b4faeebea3c5
Create Date: 2024-05-16 10:58:13.841721

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM


# revision identifiers, used by Alembic.
revision: str = 'a64940c1c4bb'
down_revision: Union[str, None] = 'b4faeebea3c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define the enum type
mou_review_decision_enum = ENUM('VERIFIED', 'NOT_YET_VERIFIED', name='moureviewdecision', create_type=False)


def upgrade() -> None:
    # Create the enum type
    mou_review_decision_enum.create(op.get_bind())

    # Add the column with the newly created enum type
    op.add_column('mou_review', sa.Column('decision', mou_review_decision_enum, nullable=False))


def downgrade() -> None:
    # Drop the column first
    op.drop_column('mou_review', 'decision')

    # Drop the enum type
    mou_review_decision_enum.drop(op.get_bind())