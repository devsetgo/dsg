# -*- coding: utf-8 -*-
"""
Jinja2 rendering for Robyn.

Robyn's JinjaTemplate has no request context and no `url_for`, so the
globals templates rely on (static URLs with a cache-busting version, the app
version, the active path for the sidebar) are provided here.
"""

import os
from functools import lru_cache

from robyn import Headers, Response
from robyn.templating import JinjaTemplate

from .settings import settings

TEMPLATE_DIR = "templates"
STATIC_DIR = "static"
STATIC_ROUTE = "/static"

_engine = JinjaTemplate(TEMPLATE_DIR)


@lru_cache(maxsize=256)
def _static_version(path: str) -> int:
    # Cached per process: files only change on deploy, which restarts workers.
    try:
        return int(os.path.getmtime(os.path.join(STATIC_DIR, path)))
    except OSError:
        return 0


def static_url(path: str) -> str:
    return f"{STATIC_ROUTE}/{path}?v={_static_version(path)}"


_engine.env.globals.update(
    static_url=static_url,
    app_version=settings.version,
)


def render_string(template_name: str, **context) -> str:
    # Read per render rather than as a global, so it follows the live setting.
    context.setdefault("public_history", settings.public_history)
    return _engine.env.get_template(template_name).render(**context)


def render(
    template_name: str,
    *,
    path: str = "",
    status_code: int = 200,
    headers: dict | None = None,
    **context,
) -> Response:
    body = render_string(template_name, path=path, **context)
    response_headers = {"Content-Type": "text/html; charset=utf-8", **(headers or {})}
    return Response(
        status_code=status_code, headers=Headers(response_headers), description=body
    )
