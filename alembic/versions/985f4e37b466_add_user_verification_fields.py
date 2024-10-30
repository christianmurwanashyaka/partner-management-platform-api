"""add user verification fields

Revision ID: 985f4e37b466
Revises: 677d9ea249a3
Create Date: 2024-10-30 20:33:29.938490

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "985f4e37b466"
down_revision: Union[str, None] = "677d9ea249a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Check if columns exist before adding them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("user")]

    # Add is_verified if it doesn't exist
    if "is_verified" not in columns:
        op.add_column(
            "user",
            sa.Column(
                "is_verified", sa.Boolean(), server_default="true", nullable=False
            ),
        )

    # Add has_set_password if it doesn't exist
    if "has_set_password" not in columns:
        op.add_column(
            "user",
            sa.Column(
                "has_set_password", sa.Boolean(), server_default="true", nullable=False
            ),
        )

    # Update the default for new records to False
    op.alter_column("user", "is_verified", server_default="false")
    op.alter_column("user", "has_set_password", server_default="false")


def downgrade() -> None:
    # Check if columns exist before dropping them
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col["name"] for col in inspector.get_columns("user")]

    if "has_set_password" in columns:
        op.drop_column("user", "has_set_password")
    if "is_verified" in columns:
        op.drop_column("user", "is_verified")
