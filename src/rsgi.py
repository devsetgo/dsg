# -*- coding: utf-8 -*-
"""
The Granian server for the DevSetGo package resolver, through RSGI (Granian's
native interface).

The handlers live in src/routes/ and know nothing about the server; this
module is the RSGI adapter (src/main.py is the one for Robyn).

Run with:
    granian --interface rsgi --workers 8 --loop uvloop --no-ws src.rsgi:app
    make run-dev                                     (hot reload)

Differences from the Robyn server:
- multipart/form-data bodies are not parsed (the form posts urlencoded);
- request bodies are capped at MAX_BODY_BYTES;
- there is no app-level access log; use Granian's --access-log.
"""

import mimetypes
import time
from pathlib import Path
from urllib.parse import parse_qsl

from dsg_lib.web_common.health import calculate_uptime
from loguru import logger

from . import resources
from .logs import configure_logging
from .routes import api, pages
from .routes.errors import error_page
from .settings import settings
from .templating import STATIC_DIR, STATIC_ROUTE
from .web import Matcher, Reply, Request, Route, json_reply

configure_logging()

# Far above the form's 20,000-character limit; this only stops a client from
# making a worker buffer an arbitrarily large body.
MAX_BODY_BYTES = 1_048_576
STATIC_ROOT = Path(STATIC_DIR).resolve()
STATIC_PREFIX = f"{STATIC_ROUTE}/"
STARTED = time.time()


async def health_status(request: Request) -> Reply:
    return json_reply({"status": "UP"})


async def health_uptime(request: Request) -> Reply:
    return json_reply(calculate_uptime(STARTED))


def _routes() -> list[Route]:
    routes = [*pages.ROUTES, *api.ROUTES]
    if settings.health_status_endpoint:
        routes.append(Route("GET", "/api/health/status", health_status))
    if settings.health_uptime_endpoint:
        routes.append(Route("GET", "/api/health/uptime", health_uptime))
    return routes


MATCHER = Matcher(_routes())


class BodyTooLarge(Exception):
    pass


async def _read_body(proto) -> bytes:
    chunks: list[bytes] = []
    size = 0
    async for chunk in proto:
        size += len(chunk)
        if size > MAX_BODY_BYTES:
            raise BodyTooLarge
        chunks.append(chunk)
    return b"".join(chunks)


def _peer(client: str) -> str | None:
    """'203.0.113.7:51234' or '[::1]:51234' -> the address."""
    host = client.rsplit(":", 1)[0] if client else ""
    return host.strip("[]") or None


def _wire(reply: Reply) -> list[tuple[str, str]]:
    # HTTP/2 requires lower-case header names.
    return [(name.lower(), value) for name, value in reply.headers.items()]


def _serve_static(path: str, proto) -> None:
    candidate = (STATIC_ROOT / path[len(STATIC_PREFIX) :]).resolve()
    if "\0" in path or not candidate.is_relative_to(STATIC_ROOT) or not candidate.is_file():
        reply = error_page(404)
        proto.response_str(reply.status, _wire(reply), reply.body)
        return
    kind = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
    # URLs carry ?v=<mtime> (see templating.static_url), so a stale copy
    # can't outlive a deploy.
    proto.response_file(
        200,
        [("content-type", kind), ("cache-control", "public, max-age=3600")],
        str(candidate),
    )


class App:
    # Granian calls these once per worker, around the event loop's lifetime.
    # The loop is not running yet in __rsgi_init__, so startup (the httpx
    # client, the database) can run to completion on the loop requests will use.
    def __rsgi_init__(self, loop) -> None:
        loop.run_until_complete(resources.startup())

    def __rsgi_del__(self, loop) -> None:
        loop.run_until_complete(resources.shutdown())

    async def __rsgi__(self, scope, proto) -> None:
        if scope.proto != "http":
            return
        path = scope.path
        if path.startswith(STATIC_PREFIX) and scope.method == "GET":
            _serve_static(path, proto)
            return
        try:
            reply = await self._dispatch(scope, proto)
        except BodyTooLarge:
            reply = error_page(400, "That request is too large.")
        except Exception as exc:
            logger.opt(exception=exc).error(f"unhandled error: {exc}")
            reply = error_page(
                500, "Something went wrong on our side. The error has been logged."
            )
        proto.response_str(reply.status, _wire(reply), reply.body)

    async def _dispatch(self, scope, proto) -> Reply:
        method, path = scope.method, scope.path
        found = MATCHER.match(method, path)
        if found is None:
            if MATCHER.allowed_methods(path):
                return error_page(405)
            return error_page(404)
        route, params = found
        body = await _read_body(proto) if method == "POST" else b""
        request = Request(
            method=method,
            path=path,
            headers=scope.headers,
            query=dict(parse_qsl(scope.query_string, keep_blank_values=True)),
            body=body,
            client_ip=_peer(scope.client),
            path_params=params,
        )
        return await route.handler(request)


app = App()
