import uuid
from datetime import datetime

from sqlalchemy import func, and_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Selectable
from sqlalchemy.orm import selectinload, aliased, contains_eager, outerjoin
from typing import Any, Optional

from db.models import MouReview, MouApproval, MouApplication, Project, BudgetType, FundingUnit, FundingSource, Goal, \
    Activity, ActivityDomain, InputDetail, DomainIntervention, SubDomain, InputCategory, Input, Party, MouDetail, \
    Document
from db.models.domain import SubDomainFunction, SubFunction
from db.models.pagination import PaginatedResponse
from schemas.activity import ActivityRead, ActivityDomainDetail
from schemas.input_detail import InputDetailRead
from schemas.mou_detail import MouDetailRead


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


async def load_project_related_objects(db: AsyncSession, project: Project, load_goals: bool = False) -> None:
    budget_type = (
        await db.execute(select(BudgetType).where(BudgetType.uuid == project.budget_type_id))
    ).scalars().first()

    funding_unit = (
        await db.execute(select(FundingUnit).where(FundingUnit.uuid == project.funding_unit_id))
    ).scalars().first()

    funding_source = (
        await db.execute(select(FundingSource).where(FundingSource.uuid == project.funding_source_id))
    ).scalars().first()

    project.budget_type = budget_type
    project.funding_unit = funding_unit
    project.funding_source = funding_source

    if load_goals:
        goals = (
            await db.execute(select(Goal).where(Goal.project_id == project.uuid))
        ).scalars().all()
        project.goals = goals


async def load_activity_related_entities(db: AsyncSession, activity: Activity):
    domains_query = select(ActivityDomain).where(
        ActivityDomain.activity_id == activity.uuid
    ).options(
        selectinload(ActivityDomain.domain_intervention),
        selectinload(ActivityDomain.sub_domain),
        selectinload(ActivityDomain.sub_domain_function),
        selectinload(ActivityDomain.sub_function)
    )
    activity.domains = (await db.execute(domains_query)).scalars().all()

    input_details_query = select(InputDetail).where(
        InputDetail.activity_id == activity.uuid
    ).options(
        selectinload(InputDetail.input_category),
        selectinload(InputDetail.input)
    )
    activity.input_details = (await db.execute(input_details_query)).scalars().all()

    return ActivityRead.from_orm(activity)

async def load_mou_detail_related_entities(db: AsyncSession, mou_detail: MouDetail):
    parties_query = select(Party).where(
        Party.mou_detail_id == mou_detail.uuid
    )
    mou_detail.parties = (await db.execute(parties_query)).scalars().all()

    project_query = select(Project).where(Project.uuid == mou_detail.project_id)
    mou_detail.project = (await db.execute(project_query)).scalar_one_or_none()

    documents_query = select(Document).where(Document.mou_detail_id == mou_detail.uuid)
    mou_detail.documents = (await db.execute(documents_query)).scalars().all()

    return MouDetailRead.from_orm(mou_detail)


async def load_full_activity_entities(db: AsyncSession, activity: Activity):
    # Query Activity Domains with related entities
    domains_query = (
        select(ActivityDomain)
        .where(ActivityDomain.activity_id == activity.uuid)
        .options(
            selectinload(ActivityDomain.domain_intervention),
            selectinload(ActivityDomain.sub_domain),
            selectinload(ActivityDomain.sub_domain_function),
            selectinload(ActivityDomain.sub_function)
        )
    )
    activity.domains = (await db.execute(domains_query)).scalars().all()

    # For each domain, ensure that related entities are loaded using select queries
    for activity_domain in activity.domains:
        if activity_domain.domain_intervention_id:
            activity_domain.domain_intervention = (
                await db.execute(
                    select(DomainIntervention).where(DomainIntervention.uuid == activity_domain.domain_intervention_id)
                )
            ).scalar_one_or_none()

        if activity_domain.sub_domain_id:
            activity_domain.sub_domain = (
                await db.execute(
                    select(SubDomain).where(SubDomain.uuid == activity_domain.sub_domain_id)
                )
            ).scalar_one_or_none()

        if activity_domain.sub_domain_function_id:
            activity_domain.sub_domain_function = (
                await db.execute(
                    select(SubDomainFunction).where(SubDomainFunction.uuid == activity_domain.sub_domain_function_id)
                )
            ).scalar_one_or_none()

        if activity_domain.sub_function_id:
            activity_domain.sub_function = (
                await db.execute(
                    select(SubFunction).where(SubFunction.uuid == activity_domain.sub_function_id)
                )
            ).scalar_one_or_none()

    # Query Input Details with related entities
    input_details_query = (
        select(InputDetail)
        .where(InputDetail.activity_id == activity.uuid)
        .options(
            selectinload(InputDetail.input_category),
            selectinload(InputDetail.input)
        )
    )
    activity.input_details = (await db.execute(input_details_query)).scalars().all()

    # For each input detail, ensure that related entities are loaded using select queries
    for input_detail in activity.input_details:
        if input_detail.input_category_id:
            input_detail.input_category = (
                await db.execute(
                    select(InputCategory).where(InputCategory.uuid == input_detail.input_category_id)
                )
            ).scalar_one_or_none()

        if input_detail.input_id:
            input_detail.input = (
                await db.execute(
                    select(Input).where(Input.uuid == input_detail.input_id)
                )
            ).scalar_one_or_none()

    # Convert to response model
    return ActivityRead.from_orm(activity)
