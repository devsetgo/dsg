# -*- coding: utf-8 -*-
"""
Entry point for the DevSetGo package resolver, a Robyn application.

Run with:
    python -m src.main --processes 2 --workers 2     (production)
    python -m src.main --dev                         (hot reload)

Robyn reads --processes/--workers/--dev from the command line itself.

Author:
    Mike Ryan

License:
    MIT License
"""

import logging
import time

from dsg_lib.common_functions import logging_config
from loguru import logger
from robyn import Headers, Request, Response, Robyn

from .resources import shutdown, startup
from .routes import api, health, pages
from .routes.errors import error_page
from .settings import settings
from .templating import STATIC_DIR, STATIC_ROUTE

logging_config.config_log(
    logging_directory=settings.logging_directory,
    log_name=settings.log_name,
    logging_level=settings.logging_level,
    log_rotation=settings.log_rotation,
    log_retention=settings.log_retention,
    log_backtrace=settings.log_backtrace,
    log_serializer=settings.log_serializer,
    log_diagnose=settings.log_diagnose,
    intercept_standard_logging=settings.log_intercept_standard_logging,
)

# httpx logs every request at INFO - hundreds of lines for one large check.
for noisy in ("httpx", "httpcore"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

app = Robyn(__file__)
app.serve_directory(STATIC_ROUTE, STATIC_DIR)
app.include_router(pages.router)
app.include_router(api.router)
app.include_router(health.router)
app.startup_handler(startup)
app.shutdown_handler(shutdown)


@app.exception
def handle_exception(error: Exception) -> Response:
    logger.opt(exception=error).error(f"unhandled error: {error}")
    return error_page(
        500, "Something went wrong on our side. The error has been logged."
    )


@app.get("/favicon.ico")
async def favicon():
    return Response(
        status_code=301,
        headers=Headers({"Location": f"{STATIC_ROUTE}/favicon.ico"}),
        description="",
    )


if settings.access_log:
    # Opt-in: each middleware is an extra Python call per request (measurable
    # in benchmarks/results), and behind Traefik its access log covers this.

    @app.before_request()
    async def stamp_start(request: Request):
        request.headers.set("x-dsg-start", str(time.perf_counter()))
        return request

    @app.after_request()
    async def access_log(request: Request, response: Response):
        started = request.headers.get("x-dsg-start")
        elapsed_ms = (time.perf_counter() - float(started)) * 1000 if started else -1
        logger.info(
            f"{request.method} {request.url.path} {response.status_code} {elapsed_ms:.1f}ms"
        )
        return response


if __name__ == "__main__":  # pragma: no cover
    # _check_port=False: on a busy port Robyn otherwise prompts on stdin for
    # another one, which hangs forever in a container instead of failing.
    app.start(host=settings.host, port=settings.port, _check_port=False)
