from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
import pandas as pd
import io
from typing import List, Optional

from api.dependencies.access_control import admin_access
from db.database import get_db
from db.models import DomainIntervention, SubDomain
from db.models.domain import SubDomainFunction, SubFunction
from schemas.domain_intervention import DomainInterventionRead

router = APIRouter()


async def get_or_create(db: AsyncSession, model, created_by: str, **kwargs):
    query = select(model).filter_by(**kwargs)
    result = await db.execute(query)
    instance = result.scalars().first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs, created_by=created_by)
        db.add(instance)
        await db.flush()
        return instance, True


@router.post("/import-excel/", response_model=List[DomainInterventionRead], dependencies=[Depends(admin_access)])
async def import_excel(
        request: UploadFile = File(...),
        db: AsyncSession = Depends(get_db)
):
    if not request.filename.endswith(('.xls', '.xlsx', '.xlsm')):
        raise HTTPException(status_code=400,
                            detail="Invalid file format. Please upload an Excel file (.xls, .xlsx, or .xlsm).")

    try:
        contents = await request.read()
        df = pd.read_excel(io.BytesIO(contents), engine='openpyxl', sheet_name="Revised Domain Classification")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not process file: {str(e)}")

    print("Columns in the Excel file:", df.columns.tolist())

    created_by = "admin@gmail.com"
    current_domain: Optional[DomainIntervention] = None
    current_subdomain: Optional[SubDomain] = None
    current_function: Optional[SubDomainFunction] = None

    for _, row in df.iterrows():
        domain_name = row['Domain'] if pd.notna(row['Domain']) else None
        subdomain_name = row['Sub Domain'] if pd.notna(row['Sub Domain']) else None
        function_name = row['Domain Functions'] if pd.notna(row['Domain Functions']) else None
        subfunction_name = row['Domain sub-function'] if pd.notna(row['Domain sub-function']) else None

        try:
            if domain_name:
                current_domain, _ = await get_or_create(db, DomainIntervention, created_by=created_by,
                                                        name=str(domain_name))
                current_subdomain = None
                current_function = None

            if subdomain_name and current_domain:
                current_subdomain, _ = await get_or_create(db, SubDomain, created_by=created_by,
                                                           name=str(subdomain_name), domain_id=current_domain.uuid)
                current_function = None

            if function_name and current_subdomain:
                current_function, _ = await get_or_create(db, SubDomainFunction, created_by=created_by,
                                                          name=str(function_name), sub_domain_id=current_subdomain.uuid)

            if subfunction_name and current_function:
                _, _ = await get_or_create(db, SubFunction, created_by=created_by, name=str(subfunction_name),
                                           function_id=current_function.uuid)

        except Exception as e:
            print(f"Error processing row: {row}")
            print(f"Error details: {str(e)}")
            # Optionally, you can choose to skip this row and continue with the next one
            # continue

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred while saving to the database: {str(e)}")

    # Fetch all created domains with their related data
    query = select(DomainIntervention).options(
        selectinload(DomainIntervention.subdomains).selectinload(SubDomain.functions).selectinload(
            SubDomainFunction.sub_functions)
    )
    result = await db.execute(query)
    created_domains = result.scalars().all()

    return created_domains
