from sqlalchemy import func, select
from sqlalchemy.orm import Session
from datetime import datetime

from uuid import UUID

from db.models import MouReview, MouApproval, MouApplication


def sync_get_most_recent_decision_time(session: Session, mou_application_id: UUID) -> datetime:
    # Query for the most recent review and approval
    query = select(
        func.greatest(
            func.coalesce(func.max(MouReview.created_at), datetime.min),
            func.coalesce(func.max(MouApproval.created_at), datetime.min)
        ).label('most_recent_time'),
        func.count(MouReview.uuid).label('review_count'),
        func.count(MouApproval.uuid).label('approval_count')
    ).select_from(
        MouReview.__table__.outerjoin(MouApproval.__table__,
                                      (MouReview.mou_application_id == MouApproval.mou_application_id) &
                                      (MouReview.mou_application_id == mou_application_id)
                                      )
    )

    result = session.execute(query)
    most_recent_time, review_count, approval_count = result.first()

    if review_count == 0 and approval_count == 0:
        # If no reviews or approvals exist, get the application's last_decision_date
        app_query = select(MouApplication.last_decision_date).where(MouApplication.uuid == mou_application_id)
        app_result = session.execute(app_query)
        return app_result.scalar_one()

    return most_recent_time