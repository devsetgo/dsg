# -*- coding: utf-8 -*-
"""
Framework-neutral request/response types and routing.

The handlers in src/routes/ take a `Request` and return a `Reply`; they know
nothing about the server. Two thin adapters connect them to one: src/main.py
(Robyn) and src/rsgi.py (Granian's native RSGI interface).
"""

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Request:
    method: str
    path: str
    # Only `.get(name)` with a lower-case name is used, so each server's own
    # header object is passed through without copying.
    headers: Any
    # `.get(name, default)` returning the first value.
    query: Any
    body: str | bytes = b""
    # Parsed multipart/form-data fields, when the server provides them.
    form_data: Mapping[str, str] | None = None
    # The socket peer; behind a proxy that is the proxy (see pages.client_ip).
    client_ip: str | None = None
    path_params: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        """The body as JSON; raises ValueError when it isn't."""
        return json.loads(self.body or b"")


@dataclass(slots=True)
class Reply:
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)
    body: str = ""


def html_reply(body: str, status: int = 200) -> Reply:
    return Reply(status, {"Content-Type": "text/html; charset=utf-8"}, body)


def json_reply(payload: Any, status: int = 200) -> Reply:
    return Reply(
        status, {"Content-Type": "application/json"}, json.dumps(payload, default=str)
    )


def redirect(location: str, status: int = 303) -> Reply:
    return Reply(status, {"Location": location})


Handler = Callable[[Request], Awaitable[Reply]]


@dataclass(frozen=True, slots=True)
class Route:
    method: str
    # Robyn-style parameters: "/check/:request_group_id".
    path: str
    handler: Handler


class RouteTable(list):
    """A list of Routes with @table.get("/path") / @table.post("/path")."""

    def _add(self, method: str, path: str):
        def register(handler: Handler) -> Handler:
            self.append(Route(method, path, handler))
            return handler

        return register

    def get(self, path: str):
        return self._add("GET", path)

    def post(self, path: str):
        return self._add("POST", path)


class Matcher:
    """Finds the route for a method and path. Static paths are a dict lookup;
    paths with `:parameters` are matched segment by segment."""

    def __init__(self, routes: list[Route]) -> None:
        self._static: dict[tuple[str, str], Route] = {}
        self._dynamic: list[tuple[str, list[str], Route]] = []
        for route in routes:
            if ":" in route.path:
                self._dynamic.append((route.method, route.path.split("/"), route))
            else:
                self._static[(route.method, route.path)] = route


    def match(self, method: str, path: str) -> tuple[Route, dict[str, str]] | None:
        route = self._static.get((method, path))
        if route is not None:
            return route, {}
        parts = path.split("/")
        for route_method, pattern, route in self._dynamic:
            if route_method != method or len(pattern) != len(parts):
                continue
            params: dict[str, str] = {}
            for expected, actual in zip(pattern, parts, strict=True):
                if expected.startswith(":"):
                    if not actual:
                        break
                    params[expected[1:]] = actual
                elif expected != actual:
                    break
            else:
                return route, params
        return None

    def allowed_methods(self, path: str) -> set[str]:
        """Methods other than the one asked for that this path answers to,
        for telling a 405 from a 404."""
        allowed = {m for (m, p) in self._static if p == path}
        parts = path.split("/")
        for method, pattern, _route in self._dynamic:
            if len(pattern) == len(parts) and all(
                (a != "") if e.startswith(":") else e == a
                for e, a in zip(pattern, parts, strict=True)
            ):
                allowed.add(method)
        return allowed
