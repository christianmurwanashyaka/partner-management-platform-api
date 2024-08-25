import os
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

from sqlalchemy.engine import Engine
from sqlalchemy import event
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import time
from uvicorn.config import LOGGING_CONFIG

from api.endpoints import auth, budget_type, organization_type, funding_source, funding_unit, domain_intervention, \
    input_category, sub_domain, input, organization, user, project, activity, party, mou_detail, mou_application, mou, \
    files, sub_domain_function, sub_function, domain_data_entry, exchange_rates, statistics, report, report_activity
import uvicorn

from core.config import settings
from db.database import create_db_and_tables, async_session
from utils.security import create_admin


# Create logs directories if they don't exist
api_log_dir = "logs/api"
sql_log_dir = "logs/sql"
os.makedirs(api_log_dir, exist_ok=True)
os.makedirs(sql_log_dir, exist_ok=True)

# Get today's date
log_file_date = datetime.now().strftime("%d_%m_%Y")

# Set up API log file handler with rotation at midnight
api_log_file_path = os.path.join(api_log_dir, f"{log_file_date}.txt")
api_file_handler = TimedRotatingFileHandler(api_log_file_path, when="midnight")
api_file_handler.suffix = "%d_%m_%Y.txt"
api_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Set up SQL log file handler with rotation at midnight
sql_log_file_path = os.path.join(sql_log_dir, f"{log_file_date}.txt")
sql_file_handler = TimedRotatingFileHandler(sql_log_file_path, when="midnight")
sql_file_handler.suffix = "%d_%m_%Y.txt"
sql_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s\n\n', datefmt='%Y-%m-%d %H:%M:%S'))

# Configure the API logger
api_logger = logging.getLogger("api_logger")
api_logger.setLevel(logging.INFO)
api_logger.addHandler(api_file_handler)

# Configure the SQL logger
sql_logger = logging.getLogger("sqlalchemy.engine")
sql_logger.setLevel(logging.INFO)
sql_logger.addHandler(sql_file_handler)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop(-1)
    if total > 0.2:
        sql_logger.warning(f"Long running query: {statement}")
        sql_logger.warning(f"Total time: {total:.2f} seconds")


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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Custom middleware to log each request
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time

    # print('REQ:', request.__dict__)
    # Log the request details
    api_logger.info(
        f"Endpoint: {request.url.path} | Method: {request.method} | Status Code: {response.status_code} | Process Time: {process_time:.2f} sec")

    return response


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
app.include_router(report.router, prefix='/api/v1/report', tags=["Report"])
app.include_router(report_activity.router, prefix='/api/v1/report_activity', tags=['Report Activity'])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=7001, reload=True)
