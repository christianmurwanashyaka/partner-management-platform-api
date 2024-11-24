import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import uvicorn
from starlette.concurrency import iterate_in_threadpool

from api.endpoints import (
    auth,
    budget_type,
    organization_type,
    funding_source,
    funding_unit,
    domain_intervention,
    input_category,
    sub_domain,
    input,
    organization,
    user,
    project,
    activity,
    party,
    mou_detail,
    mou_application,
    mou,
    files,
    sub_domain_function,
    sub_function,
    domain_data_entry,
    exchange_rates,
    statistics,
    report,
    report_activity,
    health,
    financing_scheme,
    sub_financing_scheme,
    financing_agent,
    sub_financing_agent,
    health_care_provider,
    sub_health_care_provider,
)

from core.config import settings
from core.logger import (
    system_logger,
    api_logger,
    setup_exception_logging,
    setup_uvicorn_logging,
)
from db.database import create_db_and_tables, async_session
from utils.security import create_admin


async def verify_template_setup():
    template_dir = Path(__file__).parent / "templates"
    verification_template = template_dir / "emails" / "verification_email.html"
    base_template = template_dir / "emails" / "base_email.html"

    issues = []

    if not template_dir.exists():
        issues.append(f"Template directory not found: {template_dir}")

    if not verification_template.exists():
        issues.append(f"Verification template not found: {verification_template}")

    if not base_template.exists():
        issues.append(f"Base template not found: {base_template}")

    if issues:
        for issue in issues:
            print(issue)
        raise FileNotFoundError("\n".join(issues))

    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    system_logger.info("Starting up the application")
    try:
        await create_db_and_tables()
        await verify_template_setup()
        async with async_session() as db:
            await create_admin(db)
    except Exception as e:
        system_logger.error(f"Error during startup: {str(e)}\n{traceback.format_exc()}")
        raise

    yield

    # Shutdown
    system_logger.info("Shutting down the application")
    try:
        # Perform any cleanup tasks here
        pass
    except Exception as e:
        system_logger.error(
            f"Error during shutdown: {str(e)}\n{traceback.format_exc()}"
        )


# app = FastAPI(lifespan=lifespan)

app = FastAPI(
    lifespan=lifespan,
    title="Partner Management Platform",
    description="Partner MOU Management",
    version="1.0.0",
)

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

    # Initialize variables to store response info
    status_code = 500
    response_body = ""
    exception_info = None

    try:
        response = await call_next(request)
        status_code = response.status_code

        # If the request was unsuccessful, attempt to read and log the response body
        if status_code >= 400:
            response_body = [chunk async for chunk in response.body_iterator]
            response.body_iterator = iterate_in_threadpool(iter(response_body))
            response_body = b"".join(response_body).decode()

    except Exception as e:
        exception_info = f"Exception: {str(e)}\n{traceback.format_exc()}"
        # Create a JSON response for the exception
        response = JSONResponse(
            status_code=500, content={"detail": "Internal server error"}
        )

    process_time = time.time() - start_time

    # Prepare the log message
    log_msg = f"Endpoint: {request.url.path} | Method: {request.method} | Status Code: {status_code} | Process Time: {process_time:.2f} sec"

    # Add error details for unsuccessful requests
    if status_code >= 400:
        log_msg += f"\nResponse Body: {response_body}"
    if exception_info:
        log_msg += f"\n{exception_info}"

    # Log at appropriate level based on status code
    if status_code >= 500:
        api_logger.error(log_msg)
    elif status_code >= 400:
        api_logger.warning(log_msg)
    else:
        api_logger.info(log_msg)

    return response


# Include all the routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(
    budget_type.router, prefix="/api/v1/budget_type", tags=["Budget Type"]
)
app.include_router(
    exchange_rates.router,
    prefix="/api/v1/currency_exchange_rate",
    tags=["Currency Exchange Rate"],
)
app.include_router(
    organization_type.router,
    prefix="/api/v1/organization_type",
    tags=["Organization Type"],
)


app.include_router(
    financing_scheme.router,
    prefix="/api/v1/financing_scheme",
    tags=["Financing Scheme"],
)
app.include_router(
    sub_financing_scheme.router,
    prefix="/api/v1/sub_financing_scheme",
    tags=["Sub Financing Scheme"],
)
app.include_router(
    financing_agent.router, prefix="/api/v1/financing_agent", tags=["Financing Agent"]
)
app.include_router(
    sub_financing_agent.router,
    prefix="/api/v1/sub_financing_agent",
    tags=["Sub Financing Agent"],
)
app.include_router(
    health_care_provider.router,
    prefix="/api/v1/health_care_provider",
    tags=["Health Care Provider"],
)
app.include_router(
    sub_health_care_provider.router,
    prefix="/api/v1/sub_health_care_provider",
    tags=["Sub Health Care Provider"],
)


app.include_router(
    funding_source.router, prefix="/api/v1/funding_source", tags=["Funding Source"]
)
app.include_router(
    funding_unit.router, prefix="/api/v1/funding_unit", tags=["Funding Unit"]
)
app.include_router(
    domain_intervention.router,
    prefix="/api/v1/domain_intervention",
    tags=["Domain Intervention"],
)
app.include_router(sub_domain.router, prefix="/api/v1/sub_domain", tags=["Sub Domain"])
app.include_router(
    sub_domain_function.router,
    prefix="/api/v1/sub_domain_function",
    tags=["Sub Domain Function"],
)
app.include_router(
    sub_function.router, prefix="/api/v1/sub_function", tags=["Sub Function"]
)
app.include_router(
    input_category.router, prefix="/api/v1/input_category", tags=["Input Category"]
)
app.include_router(input.router, prefix="/api/v1/input", tags=["Input"])
app.include_router(
    organization.router, prefix="/api/v1/organization", tags=["Organization"]
)
app.include_router(user.router, prefix="/api/v1/user", tags=["User"])
app.include_router(project.router, prefix="/api/v1/project", tags=["Project"])
app.include_router(activity.router, prefix="/api/v1/activity", tags=["Activity"])
app.include_router(party.router, prefix="/api/v1/party", tags=["Party"])
app.include_router(mou_detail.router, prefix="/api/v1/mou_detail", tags=["MOU Detail"])
app.include_router(
    mou_application.router, prefix="/api/v1/mou_application", tags=["MOU Application"]
)
app.include_router(statistics.router, prefix="/api/v1/statistics", tags=["Statistics"])
app.include_router(mou.router, prefix="/api/v1/mou", tags=["MOU"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(
    domain_data_entry.router,
    prefix="/api/v1/domain_data_entry",
    tags=["Domain data entry"],
)
app.include_router(report.router, prefix="/api/v1/report", tags=["Report"])
app.include_router(
    report_activity.router, prefix="/api/v1/report_activity", tags=["Report Activity"]
)
app.include_router(health.router, prefix="/api/v1/health", tags=["Health"])


if __name__ == "__main__":
    setup_exception_logging()
    setup_uvicorn_logging()
    try:
        system_logger.info("Starting the application")
        uvicorn.run("main:app", host="0.0.0.0", port=7001, log_config=None)
    except SystemExit as e:
        system_logger.info(f"Application stopped with SystemExit: {e}")
    except KeyboardInterrupt:
        system_logger.info("Application stopped by user (KeyboardInterrupt)")
    except Exception as e:
        system_logger.critical(
            f"Application crashed: {str(e)}\n{traceback.format_exc()}"
        )
    finally:
        system_logger.info("Application shutdown complete")
