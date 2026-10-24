# -*- coding: utf-8 -*-
"""/api/health/status and /api/health/uptime, from dsg_lib's Robyn health router."""

import tracemalloc

from dsg_lib.robyn_functions import system_health_endpoints

from ..settings import settings

router = system_health_endpoints.create_health_router(
    {
        "enable_status_endpoint": settings.health_status_endpoint,
        "enable_uptime_endpoint": settings.health_uptime_endpoint,
        # Off: it discloses file paths and memory use on a public site.
        "enable_heapdump_endpoint": False,
    },
    prefix="/api/health",
    tags=["health"],
)
# create_health_router (2026.10.18.1) starts tracemalloc whether or not the
# heapdump endpoint exists. Tracing every allocation makes the resolver's
# allocation-heavy work ~3.5x slower, and only heapdump reads the traces.
tracemalloc.stop()
