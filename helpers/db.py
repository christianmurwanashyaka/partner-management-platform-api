from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Selectable
from sqlalchemy.orm import selectinload
from typing import Any, Optional

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


async def get_all_items(db: AsyncSession, model: Any, *, page: int = 1, page_size: int = 100, include: Optional[list] = None):
    """
    Retrieves paginated items of a specific model from the database.

    :param db: An AsyncSession instance representing the database session.
    :param model: The SQLAlchemy model class representing the table.
    :param page: The page number of the results (default: 1).
    :param page_size: The maximum number of items per page (default: 100).
    :param include: Optional list of relationship fields to eagerly load.

    :return: A tuple of total items count and a list of paginated items of the specified model.
    """

    total_items = (await db.execute(select(func.count(model.id)))).scalar_one()
    total_pages = (total_items + page_size - 1) // page_size

    query = select(model).order_by(model.created_at.desc()).offset((page - 1) * page_size).limit(page_size)

    if include:
        for field in include:
            query = query.options(selectinload(getattr(model, field)))

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
