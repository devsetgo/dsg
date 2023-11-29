# -*- coding: utf-8 -*-
import datetime

from cpuinfo import get_cpu_info
from fastapi import APIRouter, status
from fastapi.responses import ORJSONResponse, JSONResponse
from loguru import logger

from src.settings import settings

from src.toolkit.database_connector import AsyncDatabase
from src.toolkit.http_codes import (
    common_codes,
    GET_CODES,
    PATCH_CODES,
    PUT_CODES,
    POST_CODES,
    DELETE_CODES,
    generate_code_dict,
    HTTPCode,
    ALL_HTTP_CODES,
)

router = APIRouter()

# TODO: detmine method to shutdown/restart python application
# TODO: Determine method to get application uptime

# router.add_route("/metrics", handle_metrics)


simple_get_codes = generate_code_dict([200, 400, 405, 500, 503])


@router.get(
    "/status",
    status_code=status.HTTP_200_OK,
    response_class=ORJSONResponse,
    responses=simple_get_codes,
)
async def health_main() -> dict:
    """
    GET status, uptime, and current datetime

    Returns:
        dict -- [status: UP, uptime: seconds current_datetime: datetime.now]
    """
    status = {"status": "UP"}
    logger.info(status)
    return status


@router.get("/system-info", response_class=ORJSONResponse, responses=GET_CODES)
async def health_status() -> dict:
    """
    GET Request for CPU and process data

    Returns:
        dict -- [current_datetime: datetime.now, system information:
        Python and System Information]
    """

    try:
        system_info = get_cpu_info()
        result: dict = {
            "current_datetime": str(datetime.datetime.now()),
            "system_info": system_info,
        }
        logger.info("GET system info")
        return result
        # TODO: make more specific Exception
        # BODY: Exception is generic and should be more specific or removed.
    except Exception as e:
        logger.error(f"Error: {e}")


@router.get("/db-connections", response_class=ORJSONResponse, responses=GET_CODES)
async def get_db_connections():
    # Get the connection pool's status
    pool_status = AsyncDatabase.engine.pool.status()

    return pool_status


# @router.get("/processes", tags=["system-health"])
# async def health_processes() -> dict:
#     """
#     GET running processes and filter by python processes

#     Returns:
#         dict -- [pid, name, username]
#     """
#     try:
#         system_info = get_processes()
#         result: dict = {
#             "current_datetime": str(datetime.datetime.now()),
#             # "note": "this is filter to only return, python, gunicorn,
#             # uvicorn, hypercorn, and daphne pids for security",
#             "running_processes": system_info,
#         }
#         logger.info("GET processes")
#         return result
#     except Exception as e:
#         logger.error(f"Error: {e}")


# @router.get("/configuration")
# async def configuration():
#     """
#     API information endpoint

#     Returns:
#         [json] -- [description] app version, environment running in (dev/prd),
#         Doc/Redoc link, Lincense information, and support information
#     """
#     configuration: dict = config_settings.dict()

#     # remove sensitive data
#     exclude_config: list = [
#         "sqlalchemy_database_uri",
#         "db_name",
#         "database_type",
#         "secret_key",
#         "create_sample_data",
#         "number_tasks",
#         "number_users",
#         "number_groups",
#     ]
#     logger.debug(f"excluding {exclude_config}")
#     for e in exclude_config:
#         if e in configuration:
#             configuration.pop(e)

#     result = {
#         # "docs": {"OpenAPI": openapi_url, "ReDoc": redoc_url},
#         "configuraton": configuration,
#     }
#     return result
