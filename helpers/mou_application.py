from datetime import datetime
from typing import Optional, List

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import or_, and_, func, select, distinct
from sqlmodel.ext.asyncio.session import AsyncSession

from db.models import User, MouApplication, Project, ActivityDomain, InputDetail, MOHStaffLevel, MouApplicationStatus, \
    Organization, Activity, Input, InputCategory, DomainIntervention, SubDomain, FundingSource, FundingUnit, BudgetType, \
    OrganizationType, MouDetail
from db.models.domain import SubDomainFunction, SubFunction
from schemas.mou_application import MouApplicationOrganizationRead
from utils.filters import parse_uuid_list, parse_string_list


class PaginationParams(BaseModel):
    page: int = Query(1, description='Page number')
    page_size: int = Query(100, description='Page size')

class AllApplicationsFilters(BaseModel):
    organization_uuids: Optional[List[str]]
    funding_source_uuids: Optional[List[str]]
    funding_unit_uuids: Optional[List[str]]
    budget_type_uuids: Optional[List[str]]
    domain_intervention_uuids: Optional[List[str]]
    sub_domain_uuids: Optional[List[str]]
    sub_domain_function_uuids: Optional[List[str]]
    sub_function_uuids: Optional[List[str]]
    input_category_uuids: Optional[List[str]]
    input_uuids: Optional[List[str]]
    districts: Optional[List[str]]
    provinces: Optional[List[str]]
    application_status: Optional[List[str]]
    next_levels: Optional[List[str]]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    search: Optional[str]


def get_filters(
    organization_uuids: Optional[List[str]] = Query(None),
    funding_source_uuids: Optional[List[str]] = Query(None),
    funding_unit_uuids: Optional[List[str]] = Query(None),
    budget_type_uuids: Optional[List[str]] = Query(None),
    domain_intervention_uuids: Optional[List[str]] = Query(None),
    sub_domain_uuids: Optional[List[str]] = Query(None),
    sub_domain_function_uuids: Optional[List[str]] = Query(None),
    sub_function_uuids: Optional[List[str]] = Query(None),
    input_category_uuids: Optional[List[str]] = Query(None),
    input_uuids: Optional[List[str]] = Query(None),
    districts: Optional[List[str]] = Query(None),
    provinces: Optional[List[str]] = Query(None),
    application_status: Optional[List[str]] = Query(None),
    next_levels: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = Query(
        default=datetime(1970, 1, 1),
        description="Filter applications created on or after this date"
    ),
    end_date: Optional[datetime] = Query(
        default=datetime(9999, 12, 31),
        description="Filter applications created on or before this date"
    ),
    search: Optional[str] = Query(None, description="Search query for names")
) -> AllApplicationsFilters:
    # Return the filters as a Pydantic model instance
    return AllApplicationsFilters(
        organization_uuids=organization_uuids,
        funding_source_uuids=funding_source_uuids,
        funding_unit_uuids=funding_unit_uuids,
        budget_type_uuids=budget_type_uuids,
        domain_intervention_uuids=domain_intervention_uuids,
        sub_domain_uuids=sub_domain_uuids,
        sub_domain_function_uuids=sub_domain_function_uuids,
        sub_function_uuids=sub_function_uuids,
        input_category_uuids=input_category_uuids,
        input_uuids=input_uuids,
        districts=districts,
        provinces=provinces,
        application_status=application_status,
        next_levels=next_levels,
        start_date=start_date,
        end_date=end_date,
        search=search
    )


class SortingParams(BaseModel):
    sort_by: Optional[str] = Query(None, description="Field to sort by: status, budget, created_at")
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")


class MouApplicationFilters(BaseModel):
    organization_uuids: Optional[List[str]] = Query(None)
    funding_source_uuids: Optional[List[str]] = Query(None)
    funding_unit_uuids: Optional[List[str]] = Query(None)
    budget_type_uuids: Optional[List[str]] = Query(None)
    domain_intervention_uuids: Optional[List[str]] = Query(None)
    sub_domain_uuids: Optional[List[str]] = Query(None)
    sub_domain_function_uuids: Optional[List[str]] = Query(None)
    sub_function_uuids: Optional[List[str]] = Query(None)
    input_category_uuids: Optional[List[str]] = Query(None)
    input_uuids: Optional[List[str]] = Query(None)
    districts: Optional[List[str]] = Query(None)
    provinces: Optional[List[str]] = Query(None)
    application_status: Optional[List[str]] = Query(None)
    next_levels: Optional[List[str]] = Query(None)
    start_date: Optional[datetime] = Query(
        default=datetime(1970, 1, 1),
        description="Filter applications created on or after this date")
    end_date: Optional[datetime] = Query(
        default=datetime(9999, 12, 31),
        description="Filter applications created on or before this date")
    sort_by: Optional[str] = Query(None, description="Field to sort by: status, budget, created_at")
    order: Optional[str] = Query("desc", description="Sort order: asc or desc")
    search: Optional[str] = Query(None, description="Search query for names")

    def __init__(self, **data):
        super().__init__(**data)
        self.parse_filters()

    def parse_filters(self):
        # Parse URL-encoded, comma-separated UUIDs and strings
        self.organization_uuids = parse_uuid_list(self.organization_uuids)
        self.funding_source_uuids = parse_uuid_list(self.funding_source_uuids)
        self.funding_unit_uuids = parse_uuid_list(self.funding_unit_uuids)
        self.budget_type_uuids = parse_uuid_list(self.budget_type_uuids)
        self.domain_intervention_uuids = parse_uuid_list(self.domain_intervention_uuids)
        self.sub_domain_uuids = parse_uuid_list(self.sub_domain_uuids)
        self.sub_domain_function_uuids = parse_uuid_list(self.sub_domain_function_uuids)
        self.sub_function_uuids = parse_uuid_list(self.sub_function_uuids)
        self.input_category_uuids = parse_uuid_list(self.input_category_uuids)
        self.input_uuids = parse_uuid_list(self.input_uuids)
        self.districts = parse_string_list(self.districts)
        self.provinces = parse_string_list(self.provinces)
        self.application_status = parse_string_list(self.application_status)
        self.next_levels = parse_string_list(self.next_levels)


def build_base_query(filters: MouApplicationFilters, current_user: User):
    # Base query to select fields
    base_query = select(
        MouApplication.created_at,
        MouApplication.submitted_by,
        MouApplication.uuid,
        MouApplication.status,
        MouApplication.next_level,
        Organization.name.label('organization'),
        OrganizationType.name.label('organization_type')
    )

    calculate_budget = filters.sort_by == 'budget'
    # Add budget calculation if needed
    if calculate_budget:
        budget_subquery = (
            select(
                Activity.project_id,
                func.sum(InputDetail.budget).label('total_budget')
            )
            .join(InputDetail.activity)
            .group_by(Activity.project_id)
            .subquery()
        )
        base_query = base_query.add_columns(
            func.coalesce(budget_subquery.c.total_budget, 0).label('total_budget')
        )

    # Joins for base query
    base_query = base_query.join(MouApplication.mou_detail) \
        .join(MouDetail.project) \
        .join(Project.organization) \
        .join(Organization.organization_type)

    if calculate_budget:
        base_query = base_query.outerjoin(budget_subquery, Project.uuid == budget_subquery.c.project_id)

    # Additional joins for filtering and search
    base_query = base_query.join(Project.activities) \
        .join(Activity.domains) \
        .join(Activity.input_details) \
        .join(InputDetail.input) \
        .join(InputDetail.input_category) \
        .join(ActivityDomain.domain_intervention) \
        .join(ActivityDomain.sub_domain) \
        .join(ActivityDomain.sub_domain_function) \
        .join(ActivityDomain.sub_function) \
        .join(Project.funding_source) \
        .join(Project.funding_unit) \
        .join(Project.budget_type)

    # Group by columns
    group_by_columns = [
        MouApplication.uuid,
        MouApplication.created_at,
        MouApplication.submitted_by,
        MouApplication.status,
        MouApplication.next_level,
        Organization.name,
        OrganizationType.name
    ]

    if calculate_budget:
        group_by_columns.append(budget_subquery.c.total_budget)

    base_query = base_query.group_by(*group_by_columns)

    return base_query


def apply_filters(
        base_query,
        filters: MouApplicationFilters,
        current_user: User
):
    filter_conditions = []

    # Apply filters based on user role
    if current_user.role == 'partner':
        filter_conditions.append(MouApplication.created_by == current_user.email)

    # Apply filters from the filters object
    if filters.organization_uuids:
        filter_conditions.append(Project.organization_id.in_(filters.organization_uuids))
    if filters.funding_source_uuids:
        filter_conditions.append(Project.funding_source_id.in_(filters.funding_source_uuids))
    if filters.funding_unit_uuids:
        filter_conditions.append(Project.funding_unit_id.in_(filters.funding_unit_uuids))
    if filters.budget_type_uuids:
        filter_conditions.append(Project.budget_type_id.in_(filters.budget_type_uuids))
    if filters.domain_intervention_uuids:
        filter_conditions.append(ActivityDomain.domain_intervention_id.in_(filters.domain_intervention_uuids))
    if filters.sub_domain_uuids:
        filter_conditions.append(ActivityDomain.sub_domain_id.in_(filters.sub_domain_uuids))
    if filters.sub_domain_function_uuids:
        filter_conditions.append(ActivityDomain.sub_domain_function_id.in_(filters.sub_domain_function_uuids))
    if filters.sub_function_uuids:
        filter_conditions.append(ActivityDomain.sub_function_id.in_(filters.sub_function_uuids))
    if filters.input_category_uuids:
        filter_conditions.append(InputDetail.input_category_id.in_(filters.input_category_uuids))
    if filters.input_uuids:
        filter_conditions.append(InputDetail.input_id.in_(filters.input_uuids))
    if filters.districts:
        filter_conditions.append(InputDetail.district.in_(filters.districts))
    if filters.provinces:
        filter_conditions.append(InputDetail.province.in_(filters.provinces))
    if filters.next_levels:
        next_level_filter = []
        for level in filters.next_levels:
            if level == MOHStaffLevel.PARTNER_COORDINATOR.value:
                next_level_filter.append(
                    or_(
                        MouApplication.status == MouApplicationStatus.PENDING,
                        MouApplication.next_level == MOHStaffLevel.PARTNER_COORDINATOR
                    )
                )
            elif level in [MOHStaffLevel.LEGAL_ADVISOR.value, MOHStaffLevel.TECHNICAL_DEPARTMENT.value]:
                next_level_filter.append(
                    or_(
                        and_(
                            MouApplication.status == MouApplicationStatus.UNDER_REVIEW,
                            MouApplication.next_level.is_(None)
                        ),
                        MouApplication.next_level == level
                    )
                )
            else:
                next_level_filter.append(MouApplication.next_level == level)
        filter_conditions.append(or_(*next_level_filter))
    if filters.application_status:
        filter_conditions.append(MouApplication.status.in_(filters.application_status))

    # Date range filters
    filter_conditions.append(MouApplication.created_at >= filters.start_date)
    filter_conditions.append(MouApplication.created_at <= filters.end_date)

    # Search filter
    if filters.search:
        search_filter = or_(
            Organization.name.ilike(f"%{filters.search}%"),
            Activity.name.ilike(f"%{filters.search}%"),
            Input.name.ilike(f"%{filters.search}%"),
            InputCategory.name.ilike(f"%{filters.search}%"),
            DomainIntervention.name.ilike(f"%{filters.search}%"),
            SubDomain.name.ilike(f"%{filters.search}%"),
            SubDomainFunction.name.ilike(f"%{filters.search}%"),
            SubFunction.name.ilike(f"%{filters.search}%"),
            FundingSource.name.ilike(f"%{filters.search}%"),
            FundingUnit.name.ilike(f"%{filters.search}%"),
            BudgetType.name.ilike(f"%{filters.search}%")
        )
        filter_conditions.append(search_filter)

    # Apply filters to the base query
    for filter_condition in filter_conditions:
        base_query = base_query.filter(filter_condition)

    return base_query


def apply_sorting(query, sort_by: Optional[str], order: str):
    if sort_by == 'status':
        order_by = MouApplication.status.desc() if order == 'desc' else MouApplication.status.asc()
    elif sort_by == 'budget':
        order_by = query.c.total_budget.desc() if order == 'desc' else query.c.total_budget.asc()
    elif sort_by == 'created_at':
        order_by = MouApplication.created_at.desc() if order == 'desc' else MouApplication.created_at.asc()
    else:
        order_by = MouApplication.created_at.desc()  # Default sorting

    return query.order_by(order_by)


async def count_total_items(query, db: AsyncSession):
    count_query = select(func.count(distinct(MouApplication.uuid))).select_from(
        query.with_only_columns(MouApplication.uuid).subquery()
    )
    return (await db.execute(count_query)).scalar_one()


def prepare_response(app, calculate_budget: bool):
    return MouApplicationOrganizationRead(
        created_at=app.created_at,
        submitted_by=app.submitted_by,
        reference_number=f"{app.created_at:%Y%m%d}-{app.uuid.int % 1000000:06d}",
        uuid=app.uuid,
        status=app.status,
        organization=app.organization,
        organization_type=app.organization_type,
        next_level=app.next_level,
        total_budget=app.total_budget if calculate_budget else None
    )

