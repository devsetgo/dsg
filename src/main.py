# -*- coding: utf-8 -*-
"""
This module, `main.py`, serves as the entry point for a FastAPI application named DevSetGo.com. It is responsible for configuring the application's logging, middleware, routes, and lifecycle events. The application provides a set of APIs for various functionalities, including note metrics and user management, with detailed API documentation available through FastAPI's built-in support for OpenAPI.

The module utilizes the `asynccontextmanager` from the `contextlib` module to define an asynchronous context manager for the application's lifespan events, ensuring proper startup and shutdown procedures are followed. It also integrates custom modules for logging configuration, middleware setup, route creation, and application settings.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating and configuring the FastAPI application.
    - loguru: For application logging.
    - contextlib: For the asynchronous context manager.
    - .app_middleware: Module for adding middleware to the application.
    - .app_routes: Module for defining application routes.
    - .functions.notes_metrics: Module for note metrics functionalities.
    - .resources.startup: Module for startup tasks.
    - .settings: Module for application settings.

Functions:
    - lifespan(app: FastAPI): An asynchronous context manager for managing application startup and shutdown events.

Usage:
    This module is executed to start the FastAPI application, setting up logging, middleware, routes, and handling the application's lifespan events. It configures the application with a title, description, version, and documentation URLs, and initializes it with specified settings for debugging, middleware, and routes.
"""
import signal
from contextlib import asynccontextmanager

from dsg_lib.common_functions import logging_config
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from loguru import logger

from .app_middleware import add_middleware
from .app_routes import create_routes
from .functions.notes_metrics import all_note_metrics
from .resources import shutdown, startup
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
    log_propagate=False,
    intercept_standard_logging=False,
)


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    logger.info("starting up")
    await startup()
    await all_note_metrics()
    yield
    await shutdown()


# Create an instance of the FastAPI class
app = FastAPI(
    title="DevSetGo.com",  # The title of the API
    description="Website for devsetgo.com",  # A brief description of the API
    version=settings.version,  # The version of the API
    docs_url="/docs",  # The URL where the API documentation will be served
    redoc_url="/redoc",  # The URL where the ReDoc documentation will be served
    openapi_url="/openapi.json",  # The URL where the OpenAPI schema will be served
    debug=settings.debug_mode,  # Enable debug mode
    middleware=[],  # A list of middleware to include in the application
    routes=[],  # A list of routes to include in the application
    lifespan=lifespan,
    # exception_handlers=
)
if settings.debug_mode:  # pragma: no cover
    logger.warning("Debug mode is enabled and should not be used in production.")

# add middleware and routes to the application
add_middleware(app)
# create routes
create_routes(app)


# Define a signal handler for the WINCH signal
def handle_winch(signum, frame):
    logger.info("Received WINCH signal")


# Register the signal handler
signal.signal(signal.SIGWINCH, handle_winch)


@app.get("/")
async def root(request: Request) -> RedirectResponse:  # pragma: no cover
    """
    Root endpoint that redirects to the index page.

    This asynchronous function performs the following tasks:
    - Retrieves the 'user_identifier' from the session, if it exists.
    - Redirects the user to the '/pages/index' URL.

    Args:
        request (Request): The request object containing session data.

    Returns:
        RedirectResponse: A response that redirects the user to the '/pages/index' URL.
    """
    # Retrieve 'user_identifier' from the session, if it exists
    request.session.get("user_identifier", None)

    # Redirect the user to the '/pages/index' URL
    return RedirectResponse(url="/pages/index")
