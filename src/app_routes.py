# -*- coding: utf-8 -*-
from dsg_lib.fastapi_functions import system_health_endpoints
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect.exceptions import CsrfProtectError

from .endpoints import devtools, pages, pypi, users, notes


def create_routes(app: FastAPI):
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.exception_handler(CsrfProtectError)
    def csrf_protect_exception_handler(_: Request, exc: CsrfProtectError):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}
        )

    app.include_router(
        pages.router,
        prefix="/pages",
        tags=["html-pages"],
    )

    app.include_router(
        notes.router,
        prefix="/notes",
        tags=["notes"],
    )
    app.include_router(
        pypi.router,
        prefix="/pypi",
        tags=["pypi"],
    )
    app.include_router(
        users.router,
        prefix="/users",
        tags=["users"],
    )

    app.include_router(
        devtools.router,
        prefix="/devtools",
        tags=["devtools"],
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
    )
