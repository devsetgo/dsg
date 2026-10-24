# -*- coding: utf-8 -*-
"""
Per-client rate limiting for check submissions.

In-process and per worker process (no shared store), so the effective limit
is `checks_per_minute_per_ip x processes`. That's enough to stop one client
from monopolizing the resolver; a hard global limit belongs in the proxy.
"""

import time
from collections import OrderedDict, deque

from .settings import settings

WINDOW_SECONDS = 60
# Bound the table so a flood of distinct addresses can't grow it forever.
MAX_TRACKED_CLIENTS = 10_000

_hits: OrderedDict[str, deque[float]] = OrderedDict()


def allow(client: str | None) -> bool:
    """Record a submission from `client`; False if it's over the limit."""
    limit = settings.checks_per_minute_per_ip
    if limit <= 0:
        return True
    key = client or "unknown"
    now = time.monotonic()
    window = _hits.get(key)
    if window is None:
        window = _hits[key] = deque()
        while len(_hits) > MAX_TRACKED_CLIENTS:
            _hits.popitem(last=False)
    _hits.move_to_end(key)
    while window and now - window[0] > WINDOW_SECONDS:
        window.popleft()
    if len(window) >= limit:
        return False
    window.append(now)
    return True


def reset() -> None:
    """Forget all clients (tests)."""
    _hits.clear()
