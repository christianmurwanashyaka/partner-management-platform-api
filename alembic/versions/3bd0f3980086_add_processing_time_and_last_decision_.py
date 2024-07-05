"""Add processing_time and last_decision_date

Revision ID: 3bd0f3980086
Revises: 
Create Date: 2024-07-05 12:02:57.955986

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from uuid import UUID

from sqlalchemy import table, column, select, text
from sqlalchemy.orm import Session

from utils.functions import calculate_time_difference_ms

# revision identifiers, used by Alembic.
revision: str = '3bd0f3980086'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def get_decisions_for_application(session, application_id: UUID):
    MouReview = table('mou_review',
                      column('created_at', sa.DateTime),
                      column('uuid', sa.UUID),
                      column('mou_application_id', sa.UUID)
                      )
    MouApproval = table('mou_approval',
                        column('created_at', sa.DateTime),
                        column('uuid', sa.UUID),
                        column('mou_application_id', sa.UUID)
                        )

    reviews = session.execute(
        select(MouReview.c.created_at, MouReview.c.uuid)
        .where(MouReview.c.mou_application_id == application_id)
    ).fetchall()

    approvals = session.execute(
        select(MouApproval.c.created_at, MouApproval.c.uuid)
        .where(MouApproval.c.mou_application_id == application_id)
    ).fetchall()

    all_decisions = reviews + approvals
    return sorted(all_decisions, key=lambda x: x[0])


def upgrade() -> None:
    # Add the new columns
    op.add_column('mou_approval', sa.Column('processing_time', sa.Integer(), nullable=True))
    op.add_column('mou_review', sa.Column('processing_time', sa.Integer(), nullable=True))
    op.add_column('mou_approval', sa.Column('last_decision_date', sa.DateTime(), nullable=True))
    op.add_column('mou_review', sa.Column('last_decision_date', sa.DateTime(), nullable=True))

    # Create a session
    bind = op.get_bind()
    session = Session(bind=bind)

    try:
        MouApplication = table('mou_application',
                               column('uuid', sa.UUID),
                               column('created_at', sa.DateTime),
                               column('last_decision_date', sa.DateTime)
                               )
        MouReview = table('mou_review',
                          column('uuid', sa.UUID),
                          column('mou_application_id', sa.UUID),
                          column('created_at', sa.DateTime),
                          column('processing_time', sa.Integer),
                          column('last_decision_date', sa.DateTime)
                          )
        MouApproval = table('mou_approval',
                            column('uuid', sa.UUID),
                            column('mou_application_id', sa.UUID),
                            column('created_at', sa.DateTime),
                            column('processing_time', sa.Integer),
                            column('last_decision_date', sa.DateTime)
                            )

        # Use text() to create a raw SQL query
        applications = session.execute(text("SELECT * FROM mou_application")).fetchall()

        for application in applications:
            decisions = get_decisions_for_application(session, application.uuid)

            if not decisions:
                continue

            prev_decision_time = application.created_at
            for decision_time, decision_id in decisions:
                processing_time = calculate_time_difference_ms(prev_decision_time, decision_time)

                session.execute(
                    MouReview.update().where(MouReview.c.uuid == decision_id).values(
                        processing_time=processing_time,
                        last_decision_date=prev_decision_time
                    )
                )
                session.execute(
                    MouApproval.update().where(MouApproval.c.uuid == decision_id).values(
                        processing_time=processing_time,
                        last_decision_date=prev_decision_time
                    )
                )

                prev_decision_time = decision_time

            # Update application's last_decision_date
            session.execute(
                MouApplication.update().where(MouApplication.c.uuid == application.uuid).values(
                    last_decision_date=decisions[-1][0] if decisions else application.created_at
                )
            )

        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def downgrade() -> None:
    op.drop_column('mou_review', 'processing_time')
    op.drop_column('mou_approval', 'processing_time')
    op.drop_column('mou_review', 'last_decision_date')
    op.drop_column('mou_approval', 'last_decision_date')
