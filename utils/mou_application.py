from sqlalchemy import select
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import User


async def get_review_levels(db: AsyncSession, reviews):
    """
    Extract the staff levels of all reviewers from a list of reviews
    Args:
        db: Database Session
        reviews: List of review objects with current_review_id attribute

    Returns:
        set: a set of MOHStaffLevel values representing reviewer levels
    """
    reviewer_levels = set()

    for review in reviews:
        reviewer_query = select(User).where(User.uuid == review.current_review_id)
        reviewer = (await db.execute(reviewer_query)).scalar_one_or_none()

        if reviewer:
            reviewer_levels.add(reviewer.level)

    return reviewer_levels
