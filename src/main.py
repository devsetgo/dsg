# -*- coding: utf-8 -*-
"""
The Robyn server for the DevSetGo package resolver.

The handlers live in src/routes/ and know nothing about the server; this
module is the Robyn adapter (src/rsgi.py is the one for Granian).

Run with:
    python -m src.main --processes 8 --workers 1     (production)
    python -m src.main --dev                         (hot reload)

Robyn reads --processes/--workers/--dev from the command line itself.

Author:
    Mike Ryan

License:
    MIT License
"""

import time

from loguru import logger
from robyn import Headers, Request, Response, Robyn

from . import web
from .logs import configure_logging
from .resources import shutdown, startup
from .routes import api, health, pages
from .routes.errors import error_page
from .settings import settings
from .templating import STATIC_DIR, STATIC_ROUTE

configure_logging()

app = Robyn(__file__)
app.serve_directory(STATIC_ROUTE, STATIC_DIR)
app.include_router(health.router)
app.startup_handler(startup)
app.shutdown_handler(shutdown)


def to_request(request: Request) -> web.Request:
    return web.Request(
        method=request.method,
        path=request.url.path,
        headers=request.headers,
        query=request.query_params,
        body=request.body,
        form_data=request.form_data,
        client_ip=request.ip_addr,
        path_params=request.path_params,
    )


def to_response(reply: web.Reply) -> Response:
    return Response(
        status_code=reply.status,
        headers=Headers(reply.headers),
        description=reply.body,
    )


def robyn_view(route: web.Route):
    async def view(request: Request):
        return to_response(await route.handler(to_request(request)))

    # Robyn names OpenAPI operations after the handler; keep them distinct.
    view.__name__ = f"{route.method.lower()}_{route.path.strip('/').replace('/', '_').replace(':', '')}"
    return view


for route in [*pages.ROUTES, *api.ROUTES]:
    getattr(app, route.method.lower())(route.path)(robyn_view(route))


@app.exception
def handle_exception(error: Exception) -> Response:
    logger.opt(exception=error).error(f"unhandled error: {error}")
    return to_response(
        error_page(500, "Something went wrong on our side. The error has been logged.")
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
