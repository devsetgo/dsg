# -*- coding: utf-8 -*-

from contextlib import asynccontextmanager

from dsg_lib.common_functions import logging_config
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from .app_middleware import add_middleware
from .app_routes import create_routes
from .resources import startup
from .settings import settings

logging_config.config_log(
    logging_directory="log",
    log_name="log.log",
    logging_level="INFO",
    log_rotation="100 MB",
    log_retention="30 days",
    log_backtrace=False,
    log_format=None,
    log_serializer=False,
    log_diagnose=False,
    app_name=None,
    append_app_name=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up")
    await startup()
    # create_users = True
    # if create_users:
    #     await create_a_bunch_of_users(single_entry=23, many_entries=2000)
    yield
    logger.info("shutting down")


# Create an instance of the FastAPI class
app = FastAPI(
    title="FastAPI Example",  # The title of the API
    description="This is an example of a FastAPI application using the DevSetGo\
         Toolkit.",  # A brief description of the API
    version="0.1.0",  # The version of the API
    docs_url="/docs",  # The URL where the API documentation will be served
    redoc_url="/redoc",  # The URL where the ReDoc documentation will be served
    openapi_url="/openapi.json",  # The URL where the OpenAPI schema will be served
    debug=settings.debug_mode,  # Enable debug mode
    middleware=[],  # A list of middleware to include in the application
    routes=[],  # A list of routes to include in the application
    lifespan=lifespan,
)
if settings.debug_mode:
    logger.warning("Debug mode is enabled and should not be used in production.")

add_middleware(app)
create_routes(app)


@app.get("/")
async def root(request: Request):
    # get user_identifier from session
    user_identifier = request.session.get("user_identifier", None)
    # if user_identifier is None:
    #     return RedirectResponse(url="/users/login")
    # else:
    return RedirectResponse(url="/pages/index")
