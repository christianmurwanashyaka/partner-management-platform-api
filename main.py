from contextlib import asynccontextmanager
import logging
from sqlalchemy.engine import Engine
from sqlalchemy import event
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import time
from uvicorn.config import LOGGING_CONFIG

from api.endpoints import auth, budget_type, organization_type, funding_source, funding_unit, domain_intervention, \
    input_category, sub_domain, input, organization, user, project, activity, party, mou_detail, mou_application, mou, \
    files, sub_domain_function, sub_function, domain_data_entry, exchange_rates, statistics
import uvicorn

from db.database import create_db_and_tables, async_session
from utils.security import create_admin

LOGGING_CONFIG["loggers"] = {
    "uvicorn.error": {"level": "INFO"},
    "uvicorn.access": {"level": "INFO"},
}

# Configure logging with timestamp for FastAPI request logs
access_logger = logging.getLogger("uvicorn.access")
access_logger.setLevel(logging.INFO)

# Remove any default handlers to prevent duplicate logging
for handler in access_logger.handlers[:]:
    access_logger.removeHandler(handler)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
access_logger.addHandler(handler)

logger = logging.getLogger(__name__)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())


@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.2:
        logger.warn("Long running query: %s" % statement)
        logger.warn("Total time: %f", total)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    async with async_session() as db:
        await create_admin(db)
    yield
    print("Cleanup tasks go here")


app = FastAPI(lifespan=lifespan)

origins = ["http://localhost:5173", "http://173.249.42.7:4173", "https://ihris.hisprwanda.org:4173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(budget_type.router, prefix='/api/v1/budget_type', tags=["Budget Type"])
app.include_router(exchange_rates.router, prefix='/api/v1/currency_exchange_rate', tags=["Currency Exchange Rate"])
app.include_router(organization_type.router, prefix='/api/v1/organization_type', tags=["Organization Type"])
app.include_router(funding_source.router, prefix='/api/v1/funding_source', tags=["Funding Source"])
app.include_router(funding_unit.router, prefix='/api/v1/funding_unit', tags=["Funding Unit"])
app.include_router(domain_intervention.router, prefix='/api/v1/domain_intervention', tags=["Domain Intervention"])
app.include_router(sub_domain.router, prefix='/api/v1/sub_domain', tags=["Sub Domain"])
app.include_router(sub_domain_function.router, prefix='/api/v1/sub_domain_function', tags=["Sub Domain Function"])
app.include_router(sub_function.router, prefix='/api/v1/sub_function', tags=['Sub Function'])
app.include_router(input_category.router, prefix='/api/v1/input_category', tags=["Input Category"])
app.include_router(input.router, prefix='/api/v1/input', tags=["Input"])
app.include_router(organization.router, prefix='/api/v1/organization', tags=["Organization"])
app.include_router(user.router, prefix='/api/v1/user', tags=["User"])
app.include_router(project.router, prefix='/api/v1/project', tags=["Project"])
app.include_router(activity.router, prefix='/api/v1/activity', tags=["Activity"])
app.include_router(party.router, prefix='/api/v1/party', tags=["Party"])
app.include_router(mou_detail.router, prefix='/api/v1/mou_detail', tags=['MOU Detail'])
app.include_router(mou_application.router, prefix='/api/v1/mou_application', tags=['MOU Application'])
app.include_router(statistics.router, prefix='/api/v1/statistics', tags=['Statistics'])
app.include_router(mou.router, prefix='/api/v1/mou', tags=['MOU'])
app.include_router(files.router, prefix='/api/v1/files', tags=['Files'])
app.include_router(domain_data_entry.router, prefix='/api/v1/domain_data_entry', tags=["Domain data entry"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7001, reload=True)
