# -*- coding: utf-8 -*-
from typing import Any
from typing import Dict

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Mount
from starlette.routing import Route
from starlette.staticfiles import StaticFiles
from starlette_wtf import CSRFProtectMiddleware
from dsg_lib.logging_config import config_log
import resources
from settings import config_settings
from com_lib import exceptions
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

# from com_lib import logging_config
from endpoints.health import endpoints as health_pages
from endpoints.main import endpoints as main_pages
from endpoints.pypi_check import endpoints as pypi_pages

config_log(
    logging_directory="log",
    # or None and defaults to logging
    log_name="log.log",
    # or None and defaults to "log.log"
    logging_level=config_settings.loguru_logging_level,
    # or "info" or "debug" or "warning" or "error" or "critical" or None and defaults to "info"
    log_rotation=config_settings.loguru_rotation,
    # or None and default is 10 MB
    log_retention=config_settings.loguru_retention,
    # or None and defaults to "14 Days"
    log_backtrace=False,
    # or None and defaults to False
)
resources.init_app()

routes = [
    Route("/", endpoint=main_pages.homepage, methods=["GET"]),
    Route("/index", endpoint=main_pages.index, methods=["GET"]),
    Route("/about", endpoint=main_pages.about_page, methods=["GET"]),
    Route("/health", endpoint=health_pages.health_status, methods=["GET"]),
    Route("/pypi/check", endpoint=pypi_pages.pypi_index, methods=["GET", "POST"]),
    Route("/pypi/dashboard", endpoint=pypi_pages.pypi_data, methods=["GET"]),
    Route(
        "/pypi/results/{page}",
        endpoint=pypi_pages.pypi_result,
        methods=["GET", "POST"],
    ),
    Route("/users/login", endpoint=main_pages.login, methods=["GET", "POST"]),
    Mount("/static", app=StaticFiles(directory="static"), name="static"),
]


middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=config_settings.secret_key,
        same_site=config_settings.same_site,
        https_only=config_settings.https_on,
        max_age=config_settings.max_age,
    ),
    Middleware(CSRFProtectMiddleware, csrf_secret=config_settings.csrf_secret),
    # Middleware(HTTPSRedirectMiddleware)
]

exception_handlers: Dict[Any, Any] = {
    403: exceptions.not_allowed,
    404: exceptions.not_found,
    500: exceptions.server_error,
}


app = Starlette(
    debug=config_settings.debug,
    routes=routes,
    middleware=middleware,
    exception_handlers=exception_handlers,
    on_startup=[resources.startup],
    on_shutdown=[resources.shutdown],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app, host="0.0.0.0", port=5000, log_level="info", debug=config_settings.debug
    )
