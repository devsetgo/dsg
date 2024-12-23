# -*- coding: utf-8 -*-
"""
This module, `app_routes.py`, orchestrates the routing configuration for a FastAPI application. It is tasked with the setup of static file serving and the registration of various application endpoints, including but not limited to admin interfaces, blog posts, development tools, curated content, note-taking functionalities, general web pages, Python Package Index (PyPI) interactions, and user management.

The central function, `create_routes(app)`, is designed to integrate these routes into a given FastAPI application instance, ensuring a structured and organized approach to endpoint management.

Functions:
    create_routes(app): Integrates predefined routes and static file serving into the specified FastAPI application instance, enhancing its functionality with a diverse set of web endpoints.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: Utilized for the core web framework capabilities, including route definition and request handling.
    - loguru: Employed for logging across the application, aiding in debugging and operational monitoring.
    - starlette: Provides foundational web functionalities such as static file serving, which FastAPI builds upon.
    - dsg_lib.fastapi_functions: Contains utility functions and constants for HTTP status codes and system health checks.
    - .endpoints: A package containing individual modules for each specific application endpoint, such as admin, blog_posts, and users.
    - .resources: Houses shared resources like HTML templates, facilitating consistent response rendering across endpoints.
"""
import time
from typing import Any, Dict, NoReturn

from dsg_lib.fastapi_functions import http_codes, system_health_endpoints

# from fastapi import FastAPI, Request, HTTPException, status
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from .endpoints import (
    admin,
    blog_posts,
    devtools,
    notes,
    pages,
    pypi,
    services,
    users,
    web_links,
)
from .resources import templates


def create_routes(app: FastAPI) -> NoReturn:
    """
    Mounts routes to the provided FastAPI application instance.

    This function mounts routes for static files and various endpoints such as admin, blog_posts, devtools, web_links, notes, pages, pypi, and users.

    Args:
        app (FastAPI): The FastAPI application instance to which the routes will be mounted.

    Returns:
        NoReturn
    """
    # Mount the static files directory at the path "/static"
    # This will make the files in the "static" directory available at URLs that start with "/static"
    app.mount("/static", StaticFiles(directory="static"), name="static")

    # Record the start time for route creation
    t0 = time.time()
    site_error_routing_codes: list = [
        400,
        401,
        402,
        403,
        404,
        405,
        406,
        407,
        408,
        409,
        410,
        411,
        412,
        413,
        414,
        415,
        416,
        417,
        418,
        421,
        422,
        423,
        424,
        425,
        426,
        428,
        429,
        431,
        451,
        500,
        501,
        502,
        503,
        504,
        505,
        506,
        507,
        508,
        510,
        511,
    ]
    # Generate a dictionary of all HTTP codes
    ALL_HTTP_CODES: Dict[int, Dict[str, Any]] = http_codes.generate_code_dict(
        site_error_routing_codes
    )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> RedirectResponse:
        """
        Handles HTTP exceptions by redirecting to an error page.

        Args:
            request (Request): The request that caused the exception.
            exc (StarletteHTTPException): The exception that was raised.

        Returns:
            RedirectResponse: A response that redirects to an error page.
        """
        # Get the status code of the exception
        error_code = exc.status_code

        # If the status code is not in the dictionary of all HTTP codes, default to 500
        if error_code not in ALL_HTTP_CODES:
            error_code = 500  # default to Internal Server Error

        # Log the error
        logger.error(f"{error_code} error: {exc}")

        # Redirect to the error page for the status code
        return RedirectResponse(url=f"/error/{error_code}")

    # Include the routers for the admin, devtools, interesting things, blog posts, notes, pages, pypi, and users endpoints
    # The prefix argument specifies the path that the routes will be mounted at
    # The tags argument specifies the tags for the routes
    # The include_in_schema argument specifies whether the routes should be included in the OpenAPI schema

    show_route: bool = False
    # Make sure these are in route alphabetical order
    app.include_router(
        admin.router,
        prefix="/admin",
        tags=["admin"],
        include_in_schema=show_route,
    )

    app.include_router(
        devtools.router,
        prefix="/devtools",
        tags=["devtools"],
        include_in_schema=True,
    )

    @app.get("/error/{error_code}", include_in_schema=False)
    async def error_page(request: Request, error_code: int) -> Dict[str, Any]:
        """
        Returns an error page for the specified error code.

        Args:
            request (Request): The request that caused the error.
            error_code (int): The error code.

        Returns:
            Dict[str, Any]: A dictionary that represents the context of the error page.
        """
        # Create the context for the error page
        context = {
            "page": "x",
            "request": request,
            "error_code": error_code,
            "description": ALL_HTTP_CODES[error_code]["description"],
            "extended_description": ALL_HTTP_CODES[error_code]["extended_description"],
            "link": ALL_HTTP_CODES[error_code]["link"],
        }

        # Return a template response with the error page and the context
        return templates.TemplateResponse("error/error-page.html", context)

    app.include_router(
        services.router,
        prefix="/services/v1",
        tags=["services"],
        include_in_schema=True,
    )

    app.include_router(
        web_links.router,
        prefix="/weblinks",
        tags=["weblinks"],
        include_in_schema=show_route,
    )

    app.include_router(
        notes.router,
        prefix="/notes",
        tags=["notes"],
        include_in_schema=show_route,
    )
    app.include_router(
        pages.router,
        prefix="/pages",
        tags=["html-pages"],
        include_in_schema=show_route,
    )

    app.include_router(
        blog_posts.router,
        prefix="/posts",
        tags=["posts"],
        include_in_schema=show_route,
    )

    app.include_router(
        pypi.router,
        prefix="/pypi",
        tags=["pypi"],
        include_in_schema=show_route,
    )
    app.include_router(
        users.router,
        prefix="/users",
        tags=["users"],
        include_in_schema=show_route,
    )

    # This should always be the last route added to keep it at the bottom of the OpenAPI docs
    config_health = {
        "enable_status_endpoint": True,
        "enable_uptime_endpoint": True,
        "enable_heapdump_endpoint": True,
    }

    app.include_router(
        system_health_endpoints.create_health_router(config=config_health),
        prefix="/api/health",
        tags=["system-health"],
        include_in_schema=True,
    )

    # Log the time it took to create the routes
    logger.info(f"Routes created in {time.time()-t0:.4f} seconds")
