from typing import Optional, List

from fastapi import APIRouter, Depends, status, Query, HTTPException
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.auth import get_current_user
from db.database import get_db
from db.models import User, CurrencyExchangeRate, Project, Currency, InputDetail, Activity, ActivityDomain
from utils.filters import parse_uuid_list, parse_string_list

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
