# -*- coding: utf-8 -*-
from typing import Any
from typing import Dict

from dsg_lib.logging_config import config_log
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
from starlette_wtf import CSRFProtectMiddleware

import resources
from com_lib import exceptions
from endpoints.health import endpoints as health_pages
from endpoints.main import endpoints as main_pages
from endpoints.pypi_check import endpoints as pypi_pages
from settings import config_settings


config_log(
    logging_directory="log",
    log_name="log.log",
    logging_level=config_settings.loguru_logging_level,
    log_rotation=config_settings.loguru_rotation,
    log_retention=config_settings.loguru_retention,
    log_backtrace=False,
)

# Initialize the app
resources.init_app()

# Define the various routes for our application
routes = [
    Route("/", endpoint=main_pages.homepage, methods=["GET"]),
    Route("/index", endpoint=main_pages.index, methods=["GET"]),
    Route("/about", endpoint=main_pages.about_page, methods=["GET"]),
    Route("/health", endpoint=health_pages.health_status, methods=["GET"]),
    Route("/pypi/check", endpoint=pypi_pages.pypi_index, methods=["GET", "POST"]),
    Route("/pypi/dashboard", endpoint=pypi_pages.pypi_data, methods=["GET"]),
    Route(
        "/pypi/results/{page}", endpoint=pypi_pages.pypi_result, methods=["GET", "POST"]
    ),
    Route("/users/login", endpoint=main_pages.login, methods=["GET", "POST"]),
    Mount("/static", app=StaticFiles(directory="static"), name="static"),
]

# Add middleware to the app
middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=config_settings.secret_key,
        same_site=config_settings.same_site,
        https_only=config_settings.https_on,
        max_age=config_settings.max_age,
    ),
    Middleware(CSRFProtectMiddleware, csrf_secret=config_settings.csrf_secret),
]

# Define Exception Handlers
exception_handlers: Dict[Any, Any] = {
    403: exceptions.not_allowed,
    404: exceptions.not_found,
    500: exceptions.server_error,
}

# Setup the main Starlette application
app = Starlette(
    debug=config_settings.debug,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
    on_startup=[resources.startup],
    on_shutdown=[resources.shutdown],
)

# Start the application using uvicorn server
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=5000, log_level="info", debug=config_settings.debug
    )
