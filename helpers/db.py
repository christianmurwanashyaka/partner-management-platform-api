import uuid
from datetime import datetime

from sqlalchemy import func, and_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Selectable
from sqlalchemy.orm import selectinload, aliased, contains_eager, outerjoin
from typing import Any, Optional

from db.models import MouReview, MouApproval, MouApplication
from db.models.pagination import PaginatedResponse


async def get_first_item(db: AsyncSession, query: Selectable):
    """
    Retrieves the first item from the database based on the provided query.

    :param db: An AsyncSession instance representing the database session.
    :param query: A Selectable object representing the query to be executed.

    :return: The first item retrieved from the database.
    """
    result = await db.execute(query)
    return result.scalars().first()


async def check_if_exists(model, db: AsyncSession, **kwargs):
    """
    Generic function to check if a record exists in the database with given criteria.
    :param model: SQLAlchemy model class
    :param db: AsyncSession instance
    :param kwargs: Field names and values to filter by
    :return: Boolean indicating if a record exists
    """
    query = select(model).filter_by(**kwargs)
    try:
        result = await db.execute(query)
        if result.scalar_one_or_none() is not None:
            return True
    except NoResultFound:
        return False


async def get_all_items(
    db: AsyncSession,
    model: Any,
    *,
    page: int = 1,
    page_size: int = 100,
    include: Optional[list] = None,
    related: Optional[str] = None
):
    """
    Retrieves paginated items of a specific model from the database.

    :param db: An AsyncSession instance representing the database session.
    :param model: The SQLAlchemy model class representing the table.
    :param page: The page number of the results (default: 1).
    :param page_size: The maximum number of items per page (default: 100).
    :param include: Optional list of relationship fields to eagerly load.

    :return: A tuple of total items count and a list of paginated items of the specified model.
    """

    total_items_query = select(func.count(model.id)).where(model.deleted_status == False)
    total_items = (await db.execute(total_items_query)).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    query = select(model).where(model.deleted_status == False).order_by(model.created_at.desc()).offset(
        (page - 1) * page_size).limit(page_size)

    if include:
        for field in include:
            query = query.options(selectinload(getattr(model, field)))

    if related:
        query = query.options(selectinload(getattr(model, related)))  # Eagerly load related table

    items = (await db.execute(query)).scalars().all()

    return PaginatedResponse(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        data=items
    )


async def get_items_by_criteria(db: AsyncSession, query: Selectable):
    """
    Retrieves items from the database based on the provided query criteria.

    :param db: An AsyncSession instance representing the database session.
    :param query: A Selectable object representing the query with the desired criteria.

    :return: A list of items retrieved from the database matching the specified criteria.
    """
    result = await db.execute(query)
    return result.scalars().all()


async def get_joined_details_by_uuid(db: AsyncSession, model, alias_model, join_condition, uuid: str, relationship_option):
    """
    Retrieves joined details of a model by its UUID. This is for models that have items from another model.

    :param db: An AsyncSession instance representing the database session.
    :param model: The SQLAlchemy model class representing the table.
    :param alias_model: The SQLAlchemy model class representing the alias table.
    :param join_condition: The SQLAlchemy join condition between the model and alias model.
    :param uuid: The UUID of the model to retrieve.
    :param relationship_option: The relationship option to use for the join.

    :return: the item retrieved from the database.
    """
    alias = aliased(alias_model)

    query = (
        select(model)
        .join(alias, join_condition(alias), isouter=True)
        .filter(alias.deleted_status == False)
        .filter(model.uuid == uuid)
        .options(contains_eager(relationship_option, alias=alias)).distinct()
    )

    result = await db.execute(query)
    item = result.scalars().unique().one_or_none()

    return item


async def get_most_recent_decision_time(db: AsyncSession, mou_application_id: uuid.UUID) -> datetime:
    # Query for the most recent review and approval
    query = select(
        func.max(MouReview.created_at).label('last_review_time'),
        func.max(MouApproval.created_at).label('last_approval_time'),
        func.count(MouReview.uuid).label('review_count'),
        func.count(MouApproval.uuid).label('approval_count')
    ).select_from(
        outerjoin(MouReview, MouApproval,
                  and_(MouReview.mou_application_id == MouApproval.mou_application_id,
                       MouReview.mou_application_id == mou_application_id))
    ).where(MouReview.mou_application_id == mou_application_id)

    result = await db.execute(query)
    last_review_time, last_approval_time, review_count, approval_count = result.first()

    if review_count == 0:
        # If no reviews exist, get the application's last_decision_date
        app_query = select(MouApplication.last_decision_date).where(MouApplication.uuid == mou_application_id)
        app_result = await db.execute(app_query)
        return app_result.scalar_one()

    if approval_count == 0:
        # If there are reviews but no approvals, return the last review time
        return last_review_time

    # If there are both reviews and approvals, return the most recent of the two
    return max(last_review_time, last_approval_time)
