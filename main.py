from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.endpoints import auth, budget_type, organization_type, funding_source, funding_unit, domain_intervention, \
    input_category, sub_domain, input, organization, user, project, activity, party, mou_detail, mou_application
import uvicorn

from db.database import create_db_and_tables, async_session
from utils.security import create_admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    async with async_session() as db:
        await create_admin(db)
    yield
    print("Cleanup tasks go here")


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(budget_type.router, prefix='/api/v1/budget_type', tags=["Budget Type"])
app.include_router(organization_type.router, prefix='/api/v1/organization_type', tags=["Organization Type"])
app.include_router(funding_source.router, prefix='/api/v1/funding_source', tags=["Funding Source"])
app.include_router(funding_unit.router, prefix='/api/v1/funding_unit', tags=["Funding Unit"])
app.include_router(domain_intervention.router, prefix='/api/v1/domain_intervention', tags=["Domain Intervention"])
app.include_router(input_category.router, prefix='/api/v1/input_category', tags=["Input Category"])
app.include_router(sub_domain.router, prefix='/api/v1/sub_domain', tags=["Sub Domain"])
app.include_router(input.router, prefix='/api/v1/input', tags=["Input"])
app.include_router(organization.router, prefix='/api/v1/organization', tags=["Organization"])
app.include_router(user.router, prefix='/api/v1/user', tags=["User"])
app.include_router(project.router, prefix='/api/v1/project', tags=["Project"])
app.include_router(activity.router, prefix='/api/v1/activity', tags=["Activity"])
app.include_router(party.router, prefix='/api/v1/party', tags=["Party"])
app.include_router(mou_detail.router, prefix='/api/v1/mou_detail', tags=['MOU Detail'])
app.include_router(mou_application.router, prefix='/api/v1/mou_application', tags=['MOU Application'])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7000, reload=True)
