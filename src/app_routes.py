
from fastapi import FastAPI
from dsg_lib import system_health_endpoints
from .endpoints import pages
from fastapi.staticfiles import StaticFiles

def create_routes(app: FastAPI):


    app.mount("/static", StaticFiles(directory="static"), name="static")

    app.include_router(
        pages.router,
        prefix="/pages",
        tags=["html-pages"],
    )


    # This should always be the last route added
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