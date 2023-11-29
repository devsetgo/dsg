# -*- coding: utf-8 -*-
from datetime import datetime
from typing import List

from dsg_lib.logging_config import config_log
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field

# from sqlalchemy.future import select
from sqlalchemy import Column, Select, String

from src.endpoints import health_check, tools, users

# from .database_ops import DatabaseOperations
# from .database_connector import AsyncDatabase
# from .base_schema import SchemaBase
from src.toolkit.database_connector import AsyncDatabase
from src.toolkit.database_ops import DatabaseOperations
from src.toolkit.base_schema import SchemaBase

config_log(
    logging_directory="logs",
    log_name="log.log",
    logging_level="INFO",
    log_rotation="100 MB",
    log_retention="1 days",
    log_backtrace=True,
    log_format="{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}",
    log_serializer=False,
)


app = FastAPI()


@app.on_event("startup")
async def startup_event():
    await AsyncDatabase.create_tables()


@app.get("/")
async def root():
    return RedirectResponse("/docs", status_code=307)


# Tools router
app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["users"],
)

# Tools router
app.include_router(
    tools.router,
    prefix="/api/v1/tools",
    tags=["tools"],
)

# Health router
app.include_router(
    health_check.router,
    prefix="/api/health",
    tags=["System Health"],
)
