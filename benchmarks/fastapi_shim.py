# -*- coding: utf-8 -*-
"""
The three benchmarked endpoints served by FastAPI instead of Robyn, through
the *same* code: templates, forms, checks/DB layer and caches. Only the
framework differs, which is what the Robyn-vs-FastAPI question is about.

    uvicorn benchmarks.fastapi_shim:app --workers 4 --port 5058 --log-level warning

Needs `fastapi` and `uvicorn`, which are not app dependencies.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

from src import checks, resources
from src.db_tables import CheckStatus
from src.forms import render_check_form
from src.resolver.environment import PLATFORMS
from src.resolver.models import ResolutionReport
from src.templating import render_string


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await resources.startup()
    yield
    await resources.shutdown()


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/check", response_class=HTMLResponse)
async def check_form():
    return render_string(
        "check/form.html",
        path="/check",
        form_html=await render_check_form(),
        stats=await checks.cached_stats(),
    )


@app.get("/check/{request_group_id}", response_class=HTMLResponse)
async def check_result(request_group_id: str):
    check = await checks.get_check_for_display(request_group_id)
    if check is None:
        return HTMLResponse("not found", status_code=404)
    report = ResolutionReport.model_validate(check.report) if check.report else None
    return render_string(
        "check/result.html",
        path="/check",
        check=check,
        report=report,
        finished=check.status in CheckStatus.finished,
        platform_label=PLATFORMS[check.platform]["label"],
    )


@app.get("/api/health/status")
async def health_status():
    return JSONResponse({"status": "UP"})
