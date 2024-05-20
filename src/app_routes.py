# -*- coding: utf-8 -*-
import time

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
    interesting_things,
    notes,
    pages,
    pypi,
    users,
)
from .resources import templates


def create_routes(app: FastAPI):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    t0 = time.time()
    site_error_routing_codes = [
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
    ALL_HTTP_CODES = http_codes.generate_code_dict(site_error_routing_codes)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        error_code = exc.status_code
        if error_code not in ALL_HTTP_CODES:
            error_code = 500  # default to Internal Server Error
        logger.error(f"{error_code} error: {exc}")
        return RedirectResponse(url=f"/error/{error_code}")

    # @app.exception_handler(status.HTTP_404_NOT_FOUND)
    # async def not_found_exception_handler(request: Request, exc: HTTPException):
    #     logger.error(f"404 error: {exc}")
    #     return RedirectResponse(url=f"/error/{exc.status_code}")

    app.include_router(
        admin.router,
        prefix="/admin",
        tags=["admin"],
        include_in_schema=False,
    )

    app.include_router(
        devtools.router,
        prefix="/devtools",
        tags=["devtools"],
        include_in_schema=False,
    )

    @app.get("/error/{error_code}")
    async def error_page(request: Request, error_code: int):
        context = {
            "request": request,
            "error_code": error_code,
            "description": ALL_HTTP_CODES[error_code]["description"],
            "extended_description": ALL_HTTP_CODES[error_code]["extended_description"],
            "link": ALL_HTTP_CODES[error_code]["link"],
        }
        return templates.TemplateResponse("error/error-page.html", context)

    app.include_router(
        interesting_things.router,
        prefix="/interesting-things",
        tags=["interesting things"],
        include_in_schema=False,
    )

    app.include_router(
        blog_posts.router,
        prefix="/posts",
        tags=["posts"],
        include_in_schema=False,
    )
    app.include_router(
        notes.router,
        prefix="/notes",
        tags=["notes"],
        include_in_schema=False,
    )
    app.include_router(
        pages.router,
        prefix="/pages",
        tags=["html-pages"],
        include_in_schema=False,
    )

    app.include_router(
        pypi.router,
        prefix="/pypi",
        tags=["pypi"],
        include_in_schema=False,
    )
    app.include_router(
        users.router,
        prefix="/users",
        tags=["users"],
        include_in_schema=False,
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

    logger.info(f"Routes created in {time.time()-t0:.4f} seconds")
