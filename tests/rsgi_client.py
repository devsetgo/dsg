# -*- coding: utf-8 -*-
"""
An in-process client for the RSGI app: builds the `scope` and `proto` objects
Granian would, calls the app, and returns what it sent. It mirrors the small
part of robyn.testing.TestClient the tests use, so the same tests run against
both servers.
"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlencode


class _Headers:
    """The slice of granian.rsgi.Headers the app uses: a case-insensitive get."""

    def __init__(self, headers: dict[str, str]) -> None:
        self._headers = {k.lower(): v for k, v in headers.items()}

    def get(self, key: str, default=None):
        return self._headers.get(key.lower(), default)


class _Scope:
    proto = "http"
    http_version = "1.1"
    scheme = "http"
    client = "127.0.0.1:50000"

    def __init__(self, method, path, query_string, headers) -> None:
        self.method = method
        self.path = path
        self.query_string = query_string
        self.headers = _Headers(headers)


class _Proto:
    def __init__(self, body: bytes) -> None:
        self._body = body
        self.sent: tuple[int, dict[str, str], bytes] | None = None

    def __aiter__(self):
        async def chunks():
            # Two chunks, like a body that arrives in pieces.
            half = len(self._body) // 2
            for part in (self._body[:half], self._body[half:]):
                if part:
                    yield part

        return chunks()

    def response_str(self, status, headers, body):
        self.sent = (status, dict(headers), body.encode())

    def response_bytes(self, status, headers, body):
        self.sent = (status, dict(headers), body)

    def response_empty(self, status, headers):
        self.sent = (status, dict(headers), b"")

    def response_file(self, status, headers, path):
        self.sent = (status, dict(headers), Path(path).read_bytes())


@dataclass
class RsgiResponse:
    status_code: int
    headers: dict[str, str]
    content: bytes

    @property
    def text(self) -> str:
        return self.content.decode()

    def json(self):
        return json.loads(self.content)


class RsgiTestClient:
    kind = "rsgi"

    def __init__(self, app) -> None:
        self.app = app
        self._loop = asyncio.new_event_loop()

    def request(self, method, path, *, body="", headers=None, query_params=None):
        raw = body.encode() if isinstance(body, str) else body
        scope = _Scope(method, path, urlencode(query_params or {}), headers or {})
        proto = _Proto(raw)
        self._loop.run_until_complete(self.app.__rsgi__(scope, proto))
        assert proto.sent is not None, "the app sent no response"
        status, response_headers, content = proto.sent
        return RsgiResponse(status, response_headers, content)

    def get(self, path, *, headers=None, query_params=None):
        return self.request("GET", path, headers=headers, query_params=query_params)

    def post(self, path, *, body="", headers=None):
        return self.request("POST", path, body=body, headers=headers)

    def close(self) -> None:
        # This loop only runs during a request, so a background task (a check's
        # heartbeat, say) can still be mid-database-write when a test ends. Let
        # it unwind: a lock left held would break the next test's loop.
        leftovers = asyncio.all_tasks(self._loop)
        for task in leftovers:
            task.cancel()

        async def drain():
            await asyncio.gather(*leftovers, return_exceptions=True)

        self._loop.run_until_complete(drain())
        self._loop.close()
