from typing import Optional, List, Dict

from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy import select, func, case, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, CurrencyExchangeRate, Project, Currency, InputDetail, Activity, ActivityDomain, \
    Organization, FundingSource, FundingUnit, BudgetType, InputCategory, Input, DomainIntervention, SubDomain, \
    MouApproval, MouReview, MOHStaffLevel
from db.models.domain import SubDomainFunction, SubFunction
from utils.filters import parse_uuid_list, parse_string_list
from utils.functions import format_time_difference

router = APIRouter()


@router.get('/budget')
async def get_budget_statistics(
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
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Parse URL-encoded, comma-separated UUIDs
        organization_uuids = parse_uuid_list(organization_uuids)
        funding_source_uuids = parse_uuid_list(funding_source_uuids)
        funding_unit_uuids = parse_uuid_list(funding_unit_uuids)
        budget_type_uuids = parse_uuid_list(budget_type_uuids)
        domain_intervention_uuids = parse_uuid_list(domain_intervention_uuids)
        sub_domain_uuids = parse_uuid_list(sub_domain_uuids)
        sub_domain_function_uuids = parse_uuid_list(sub_domain_function_uuids)
        sub_function_uuids = parse_uuid_list(sub_function_uuids)
        input_category_uuids = parse_uuid_list(input_uuids)
        districts = parse_string_list(districts)
        provinces = parse_string_list(provinces)

        # Subquery to get the latest exchange rates
        latest_rates = select(CurrencyExchangeRate.currency,
                              func.max(CurrencyExchangeRate.created_at).label('max_date')). \
            group_by(CurrencyExchangeRate.currency).subquery()

        exchange_rates = select(CurrencyExchangeRate.currency, CurrencyExchangeRate.rate). \
            join(latest_rates,
                 (CurrencyExchangeRate.currency == latest_rates.c.currency) &
                 (CurrencyExchangeRate.created_at == latest_rates.c.max_date)). \
            subquery()

        # Start with a base query that joins all necessary tables
        query = select(
            func.sum(case(
                (Project.currency == Currency.RWF, InputDetail.budget),
                else_=InputDetail.budget * exchange_rates.c.rate
            )).label('total_budget_rwf'),
            func.sum(InputDetail.budget).label('total_budget_original'),
            Project.currency
        ).select_from(InputDetail). \
            join(Activity, Activity.uuid == InputDetail.activity_id). \
            join(ActivityDomain, ActivityDomain.activity_id == Activity.uuid). \
            join(Project, Project.uuid == Activity.project_id). \
            outerjoin(exchange_rates, exchange_rates.c.currency == Project.currency)


        # Apply filters
        if organization_uuids:
            query = query.filter(Project.organization_id.in_(organization_uuids))
        if funding_source_uuids:
            query = query.filter(Project.funding_source_id.in_(funding_source_uuids))
        if funding_unit_uuids:
            query = query.filter(Project.funding_unit_id.in_(funding_unit_uuids))
        if budget_type_uuids:
            query = query.filter(Project.budget_type_id.in_(budget_type_uuids))
        if domain_intervention_uuids:
            query = query.filter(ActivityDomain.domain_intervention_id.in_(domain_intervention_uuids))
        if sub_domain_uuids:
            query = query.filter(ActivityDomain.sub_domain_id.in_(sub_domain_uuids))
        if sub_domain_function_uuids:
            query = query.filter(ActivityDomain.sub_domain_function_id.in_(sub_domain_function_uuids))
        if sub_function_uuids:
            query = query.filter(ActivityDomain.sub_function_id.in_(sub_function_uuids))
        if input_category_uuids:
            query = query.filter(InputDetail.input_category_id.in_(input_category_uuids))
        if input_uuids:
            query = query.filter(InputDetail.input_id.in_(input_uuids))
        if districts:
            query = query.filter(InputDetail.district.in_(districts))
        if provinces:
            query = query.filter(InputDetail.province.in_(provinces))

        # Group by currency
        query = query.group_by(Project.currency)

        # Execute the query
        result = await db.execute(query)
        budget_data = result.fetchall()

        total_budget_rwf = 0
        total_budget_original = 0
        budgets_by_currency = {}

        for row in budget_data:
            total_budget_rwf += row.total_budget_rwf or 0
            total_budget_original += row.total_budget_original or 0
            budgets_by_currency[row.currency] = {
                "original": row.total_budget_original,
                "in_rwf": row.total_budget_rwf
            }

        return {
            "total_budget_rwf": total_budget_rwf,
            "total_budget_original": total_budget_original,
            "budgets_by_currency": budgets_by_currency,
            "filters_applied": {
                "organizations": organization_uuids,
                "funding_sources": funding_source_uuids,
                "funding_units": funding_unit_uuids,
                "budget_types": budget_type_uuids,
                "domain_interventions": domain_intervention_uuids,
                "sub_domains": sub_domain_uuids,
                "sub_domain_functions": sub_domain_function_uuids,
                "sub_functions": sub_function_uuids,
                "input_categories": input_category_uuids,
                "inputs": input_uuids,
                "districts": districts,
                "provinces": provinces
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/domain')
async def get_domain_statistics(
        organization_uuids: Optional[List[str]] = Query(None),
        funding_source_uuids: Optional[List[str]] = Query(None),
        funding_unit_uuids: Optional[List[str]] = Query(None),
        budget_type_uuids: Optional[List[str]] = Query(None),
        input_category_uuids: Optional[List[str]] = Query(None),
        input_uuids: Optional[List[str]] = Query(None),
        districts: Optional[List[str]] = Query(None),
        provinces: Optional[List[str]] = Query(None),
        appends: Optional[str] = Query(None,
                                       description="Comma-separated list of domain levels to include: domains,subdomains,subdomain_functions,subfunctions"),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Parse URL-encoded, comma-separated UUIDs and strings
        organization_uuids = parse_uuid_list(organization_uuids)
        funding_source_uuids = parse_uuid_list(funding_source_uuids)
        funding_unit_uuids = parse_uuid_list(funding_unit_uuids)
        budget_type_uuids = parse_uuid_list(budget_type_uuids)
        input_category_uuids = parse_uuid_list(input_category_uuids)
        input_uuids = parse_uuid_list(input_uuids)
        districts = parse_string_list(districts)
        provinces = parse_string_list(provinces)

        # Parse appends parameter
        append_list = [level.strip() for level in appends.split(',')] if appends else []

        # Determine which domain levels to include
        include_domains = 'domains' in append_list or not append_list
        include_subdomains = 'subdomains' in append_list
        include_subdomain_functions = 'subdomain_functions' in append_list
        include_subfunctions = 'subfunctions' in append_list

        # Base query
        query = select(
            Organization.name.label('organization_name'),
            DomainIntervention.name.label('domain_name'),
            SubDomain.name.label('subdomain_name'),
            SubDomainFunction.name.label('subdomain_function_name'),
            SubFunction.name.label('subfunction_name')
        ).select_from(ActivityDomain). \
            join(Activity, Activity.uuid == ActivityDomain.activity_id). \
            join(Project, Project.uuid == Activity.project_id). \
            join(Organization, Organization.uuid == Project.organization_id). \
            join(DomainIntervention, DomainIntervention.uuid == ActivityDomain.domain_intervention_id). \
            outerjoin(SubDomain, SubDomain.uuid == ActivityDomain.sub_domain_id). \
            outerjoin(SubDomainFunction, SubDomainFunction.uuid == ActivityDomain.sub_domain_function_id). \
            outerjoin(SubFunction, SubFunction.uuid == ActivityDomain.sub_function_id)

        # Apply filters
        if organization_uuids:
            query = query.filter(Organization.uuid.in_(organization_uuids))
        if funding_source_uuids:
            query = query.filter(Project.funding_source_id.in_(funding_source_uuids))
        if funding_unit_uuids:
            query = query.filter(Project.funding_unit_id.in_(funding_unit_uuids))
        if budget_type_uuids:
            query = query.filter(Project.budget_type_id.in_(budget_type_uuids))
        if input_category_uuids or input_uuids or districts or provinces:
            query = query.join(InputDetail, InputDetail.activity_id == Activity.uuid)
            if input_category_uuids:
                query = query.filter(InputDetail.input_category_id.in_(input_category_uuids))
            if input_uuids:
                query = query.filter(InputDetail.input_id.in_(input_uuids))
            if districts:
                query = query.filter(InputDetail.district.in_(districts))
            if provinces:
                query = query.filter(InputDetail.province.in_(provinces))

        # Execute query
        result = await db.execute(query)
        rows = result.fetchall()

        # Process results
        statistics: Dict[str, Dict] = {
            "debug_info": {"row_count": len(rows)}
        }

        for row in rows:
            org_name = row.organization_name

            if org_name not in statistics:
                statistics[org_name] = {}
                if include_domains:
                    statistics[org_name]["domains"] = {"count": 0, "names": set()}
                if include_subdomains:
                    statistics[org_name]["subdomains"] = {"count": 0, "names": set()}
                if include_subdomain_functions:
                    statistics[org_name]["subdomain_functions"] = {"count": 0, "names": set()}
                if include_subfunctions:
                    statistics[org_name]["subfunctions"] = {"count": 0, "names": set()}

            if include_domains and row.domain_name:
                statistics[org_name]["domains"]["names"].add(row.domain_name)
            if include_subdomains and row.subdomain_name:
                statistics[org_name]["subdomains"]["names"].add(row.subdomain_name)
            if include_subdomain_functions and row.subdomain_function_name:
                statistics[org_name]["subdomain_functions"]["names"].add(row.subdomain_function_name)
            if include_subfunctions and row.subfunction_name:
                statistics[org_name]["subfunctions"]["names"].add(row.subfunction_name)

        # Calculate totals and convert sets to lists
        for level in ['domains', 'subdomains', 'subdomain_functions', 'subfunctions']:
            if level in append_list or (level == 'domains' and not append_list):
                statistics[f"total_{level}"] = 0
                for group in statistics.values():
                    if isinstance(group, dict) and level in group:
                        group[level]["count"] = len(group[level]["names"])
                        group[level]["names"] = list(group[level]["names"])
                        statistics[f"total_{level}"] += group[level]["count"]

        # Add applied filters and debug info to the response
        statistics["filters_applied"] = {
            "organizations": organization_uuids,
            "funding_sources": funding_source_uuids,
            "funding_units": funding_unit_uuids,
            "budget_types": budget_type_uuids,
            "input_categories": input_category_uuids,
            "inputs": input_uuids,
            "districts": districts,
            "provinces": provinces
        }
        statistics["debug_info"]["appends"] = append_list
        statistics["debug_info"]["include_domains"] = include_domains
        statistics["debug_info"]["include_subdomains"] = include_subdomains
        statistics["debug_info"]["include_subdomain_functions"] = include_subdomain_functions
        statistics["debug_info"]["include_subfunctions"] = include_subfunctions

        return statistics

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/organizations/budget')
async def get_organizations_budget(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Subquery to get the latest exchange rates
        latest_rates = select(CurrencyExchangeRate.currency,
                              func.max(CurrencyExchangeRate.created_at).label('max_date')). \
            group_by(CurrencyExchangeRate.currency).subquery()

        exchange_rates = select(CurrencyExchangeRate.currency, CurrencyExchangeRate.rate). \
            join(latest_rates,
                 (CurrencyExchangeRate.currency == latest_rates.c.currency) &
                 (CurrencyExchangeRate.created_at == latest_rates.c.max_date)). \
            subquery()

        # Query to get total budget for each organization
        query = select(
            Organization.uuid.label('organization_id'),
            Organization.name.label('organization_name'),
            func.sum(case(
                (Project.currency == Currency.RWF, InputDetail.budget),
                else_=InputDetail.budget * exchange_rates.c.rate
            )).label('total_budget_rwf'),
            func.sum(InputDetail.budget).label('total_budget_original'),
            Project.currency
        ).select_from(Organization). \
            join(Project, Project.organization_id == Organization.uuid). \
            join(Activity, Activity.project_id == Project.uuid). \
            join(InputDetail, InputDetail.activity_id == Activity.uuid). \
            outerjoin(exchange_rates, exchange_rates.c.currency == Project.currency). \
            group_by(Organization.uuid, Organization.name, Project.currency). \
            order_by(desc('total_budget_rwf'))

        # Execute the query
        result = await db.execute(query)
        budget_data = result.fetchall()

        # Process the results
        organization_budgets = []
        for row in budget_data:
            organization_budgets.append({
                "organization_id": str(row.organization_id),
                "organization_name": row.organization_name,
                "total_budget_rwf": float(row.total_budget_rwf) if row.total_budget_rwf else 0,
                "total_budget_original": float(row.total_budget_original) if row.total_budget_original else 0,
                "currency": row.currency
            })

        return {
            "organization_budgets": organization_budgets
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/average/processing-time/reviews')
async def get_review_processing_time_statistics(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Query to get average processing time for reviews
        query = select(
            User.level,
            func.avg(MouReview.processing_time).label('avg_processing_time'),
            func.count(MouReview.uuid).label('review_count')
        ).select_from(MouReview).join(User, MouReview.current_review_id == User.uuid). \
            group_by(User.level)

        # Execute the query
        result = await db.execute(query)
        processing_times = result.fetchall()

        # Process the results
        statistics = {}
        for row in processing_times:
            level = row.level
            avg_time = int(row.avg_processing_time) if row.avg_processing_time else 0
            review_count = row.review_count

            statistics[level] = {
                'avg_processing_time_ms': avg_time,
                'formatted_time': format_time_difference(avg_time),
                'review_count': review_count
            }

        # Ensure all levels are represented, even if they have no data
        for level in MOHStaffLevel:
            if level not in statistics:
                statistics[level] = {
                    'avg_processing_time_ms': 0,
                    'formatted_time': format_time_difference(0),
                    'review_count': 0
                }

        return {
            "review_processing_time_statistics": statistics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get('/average/processing-time/approvals')
async def get_approval_processing_time_statistics(
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    try:
        # Query to get average processing time for approvals
        query = select(
            User.level,
            func.avg(MouApproval.processing_time).label('avg_processing_time'),
            func.count(MouApproval.uuid).label('approval_count')
        ).select_from(MouApproval).join(User, MouApproval.current_approver_id == User.uuid). \
            group_by(User.level)

        # Execute the query
        result = await db.execute(query)
        processing_times = result.fetchall()

        # Process the results
        statistics = {}
        for row in processing_times:
            level = row.level
            avg_time = int(row.avg_processing_time) if row.avg_processing_time else 0
            approval_count = row.approval_count

            statistics[level] = {
                'avg_processing_time_ms': avg_time,
                'formatted_time': format_time_difference(avg_time),
                'approval_count': approval_count
            }

        # Ensure all levels are represented, even if they have no data
        for level in MOHStaffLevel:
            if level not in statistics:
                statistics[level] = {
                    'avg_processing_time_ms': 0,
                    'formatted_time': format_time_difference(0),
                    'approval_count': 0
                }

        return {
            "approval_processing_time_statistics": statistics
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))