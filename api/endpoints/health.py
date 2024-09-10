import os
from typing import Tuple, Dict

import psutil
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel.ext.asyncio.session import AsyncSession

from core.logger import system_logger
from db.database import get_db

router = APIRouter()


async def check_database_connection(db: AsyncSession) -> Tuple[bool, Dict]:
    try:
        await db.execute(text("SELECT 1"))
        return True, {"message": "Database connection successful"}
    except Exception as e:
        error_message = str(e)
        system_logger.error(f"Database connection check failed: {error_message}")
        return False, {"error": error_message}


def check_disk_usage() -> Tuple[bool, Dict]:
    disk_usage = psutil.disk_usage('/')
    is_healthy = disk_usage.percent < 90
    details = {
        "total": f"{disk_usage.total / (1024**3):.2f} GB",
        "used": f"{disk_usage.used / (1024**3):.2f} GB",
        "free": f"{disk_usage.free / (1024**3):.2f} GB",
        "percent": f"{disk_usage.percent:.1f}%"
    }
    return is_healthy, details


def check_memory_usage() -> Tuple[bool, Dict]:
    memory = psutil.virtual_memory()
    is_healthy = memory.percent < 90
    details = {
        "total": f"{memory.total / (1024**3):.2f} GB",
        "available": f"{memory.available / (1024**3):.2f} GB",
        "used": f"{memory.used / (1024**3):.2f} GB",
        "percent": f"{memory.percent:.1f}%"
    }
    return is_healthy, details


def check_cpu_usage() -> Tuple[bool, Dict]:
    cpu_percent = psutil.cpu_percent(interval=1)
    is_healthy = cpu_percent < 80
    details = {
        "usage_percent": f"{cpu_percent:.1f}%",
        "core_count": psutil.cpu_count(logical=False),
        "thread_count": psutil.cpu_count(logical=True)
    }
    return is_healthy, details


@router.get("/status")
async def status(db: AsyncSession = Depends(get_db)):
    db_status, db_details = await check_database_connection(db)
    disk_status, disk_details = check_disk_usage()
    memory_status, memory_details = check_memory_usage()
    cpu_status, cpu_details = check_cpu_usage()

    components = {
        "database": {
            "status": "healthy" if db_status else "unhealthy",
            "details": db_details
        },
        "disk": {
            "status": "healthy" if disk_status else "unhealthy",
            "details": disk_details
        },
        "memory": {
            "status": "healthy" if memory_status else "unhealthy",
            "details": memory_details
        },
        "cpu": {
            "status": "healthy" if cpu_status else "unhealthy",
            "details": cpu_details
        }
    }

    overall_status = "healthy" if all(component["status"] == "healthy" for component in components.values()) else "unhealthy"

    return {
        "status": overall_status,
        "components": components
    }


@router.get("/crash")
async def force_system_crash():
    system_logger.critical("Application is about to crash (test). Note that this is a forced crash (api/v1/health/crash) made to see if the system will keep logs of crashes if they happen")
    os._exit(1)  # This will cause the application to exit immediately


