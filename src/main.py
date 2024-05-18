# -*- coding: utf-8 -*-

from contextlib import asynccontextmanager

from dsg_lib.common_functions import logging_config
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from .app_middleware import add_middleware
from .app_routes import create_routes
from .functions.notes_metrics import all_note_metrics
from .resources import startup
from .settings import settings

logging_config.config_log(
    logging_directory=settings.logging_directory,
    log_name=settings.log_name,
    logging_level=settings.logging_level,
    log_rotation=settings.log_rotation,
    log_retention=settings.log_retention,
    log_backtrace=settings.log_backtrace,
    log_format=None,
    log_serializer=settings.log_serializer,
    log_diagnose=settings.log_diagnose,
    # app_name="devsetgo",
    # append_app_name=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting up")
    await startup()

    await all_note_metrics()
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
    # exception_handlers=
)
if settings.debug_mode:
    logger.warning("Debug mode is enabled and should not be used in production.")


add_middleware(app)
create_routes(app)


@app.get("/")
async def root(request: Request):
    # get user_identifier from session
    request.session.get("user_identifier", None)
    return RedirectResponse(url="/pages/index")
