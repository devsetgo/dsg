# -*- coding: utf-8 -*-
"""HTML pages: the check form, results, history, stats and about."""

import math
from urllib.parse import parse_qs

from loguru import logger
from pydantic_schemaforms import html
from robyn import Headers, Request, Response, SubRouter

from .. import checks, limits
from ..db_tables import CheckStatus
from ..forms import render_check_form, validate_check_form
from ..resolver.environment import PLATFORMS
from ..resolver.models import ResolutionReport
from ..settings import settings
from ..templating import render, render_string
from .errors import error_page

router = SubRouter(prefix="")

HISTORY_PAGE_SIZE = 25
PLATFORM_LABELS = {key: spec["label"] for key, spec in PLATFORMS.items()}


def client_ip(request: Request) -> str | None:
    """The client's address, for the per-IP rate limit and stored checks.

    Behind Traefik the socket peer is the proxy, so read X-Forwarded-For - but
    only the entries our own proxies appended (see forwarded_proxy_hops). The
    leftmost entry is client-supplied, and trusting it would let anyone dodge
    the rate limit with a made-up header."""
    hops = settings.forwarded_proxy_hops
    forwarded = request.headers.get("x-forwarded-for") if hops > 0 else None
    if forwarded:
        entries = [entry.strip() for entry in forwarded.split(",") if entry.strip()]
        if len(entries) >= hops:
            return entries[-hops]
    return request.ip_addr


def form_fields(request: Request) -> dict[str, str]:
    """POSTed form fields. Robyn 0.88 fills request.form_data only for
    multipart/form-data; an urlencoded body (htmx's default) leaves it empty."""
    if request.form_data:
        return dict(request.form_data)
    body = request.body
    if isinstance(body, (bytes, bytearray)):
        body = body.decode("utf-8", errors="replace")
    # keep_blank_values: an emptied textarea must reach validation as "".
    return {
        key: values[-1]
        for key, values in parse_qs(body or "", keep_blank_values=True).items()
    }


def submission_refusal(request: Request) -> str | None:
    """Why a new check can't be accepted right now, or None - in which case a
    queue place is now reserved (checks.try_reserve) and the caller must hand
    it to run_check/schedule_check or release it."""
    if not limits.allow(client_ip(request)):
        return f"Too many checks from your address; the limit is {settings.checks_per_minute_per_ip} a minute."
    if not checks.try_reserve():
        return "The resolver is busy right now. Try again in a minute."
    return None


def busy_alert(message: str) -> str:
    return html(t'<div class="alert alert-warning" role="alert">{message}</div>')


def is_htmx(request: Request) -> bool:
    return (request.headers.get("hx-request") or "").lower() == "true"


async def _form_page(form_html: str, status_code: int = 200) -> Response:
    try:
        stats = await checks.cached_stats()
    except Exception as exc:
        logger.warning(f"stats unavailable: {exc}")
        stats = None
    return render(
        "check/form.html",
        path="/check",
        status_code=status_code,
        form_html=form_html,
        stats=stats,
    )


@router.get("/")
async def index():
    return await _form_page(await render_check_form())


@router.get("/check")
async def check_form():
    return await _form_page(await render_check_form())


@router.post("/check")
async def check_submit(request: Request):
    data = form_fields(request)
    result = validate_check_form(data)
    if not result.is_valid:
        form_html = await result.render_with_errors_async()
        if is_htmx(request):
            # Swapped into #check-form in place of the old form.
            return Response(
                status_code=200,
                headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
                description=form_html,
            )
        return await _form_page(form_html, status_code=422)

    busy = submission_refusal(request)
    if busy is not None:
        form_html = busy_alert(busy) + await render_check_form(data)
        if is_htmx(request):
            # htmx doesn't swap 4xx responses by default, so answer 200.
            return Response(
                status_code=200,
                headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
                description=form_html,
            )
        return await _form_page(form_html, status_code=429)

    form = result.instance
    try:
        request_group_id = await checks.create_check(
            requirements=form.requirements,
            python_version=form.python_version,
            platform=form.platform,
            mode=form.mode,
            host_ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except BaseException:
        checks.release_reservation()
        raise
    checks.schedule_check(request_group_id, reserved=True)
    location = f"/check/{request_group_id}"
    if is_htmx(request):
        return Response(
            status_code=200, headers=Headers({"HX-Redirect": location}), description=""
        )
    return Response(
        status_code=303, headers=Headers({"Location": location}), description=""
    )


async def _load(request_group_id: str):
    check = await checks.get_check_for_display(request_group_id)
    if check is not None and checks.is_stale(check):
        check.status = CheckStatus.failed
        check.error = (
            check.error
            or "This check did not finish; the server may have restarted. Please run it again."
        )
    return check


@router.get("/check/:request_group_id")
async def check_result(request: Request):
    check = await _load(request.path_params["request_group_id"])
    if check is None:
        return error_page(
            404, "That check doesn't exist. Checks are kept for a limited time."
        )
    finished = check.status in CheckStatus.finished
    report = ResolutionReport.model_validate(check.report) if check.report else None
    return render(
        "check/result.html",
        path="/check",
        check=check,
        report=report,
        finished=finished,
        platform_label=PLATFORM_LABELS.get(check.platform, check.platform),
    )


@router.get("/check/:request_group_id/status")
async def check_status(request: Request):
    check = await _load(request.path_params["request_group_id"])
    if check is None:
        return Response(
            status_code=200, headers=Headers({"HX-Redirect": "/check"}), description=""
        )
    if check.status in CheckStatus.finished:
        return Response(
            status_code=200, headers=Headers({"HX-Refresh": "true"}), description=""
        )
    return Response(
        status_code=200,
        headers=Headers({"Content-Type": "text/html; charset=utf-8"}),
        description=render_string("check/_status.html", check=check),
    )


@router.get("/history")
async def history(request: Request):
    if not settings.public_history:
        return render("history.html", path="/history", private=True)
    try:
        page = max(1, int(request.query_params.get("page", "1") or 1))
    except ValueError:
        page = 1
    rows, total = await checks.recent_checks(
        limit=HISTORY_PAGE_SIZE, offset=(page - 1) * HISTORY_PAGE_SIZE
    )
    return render(
        "history.html",
        path="/history",
        checks=rows,
        total=total,
        page=page,
        pages=max(1, math.ceil(total / HISTORY_PAGE_SIZE)),
        platform_labels=PLATFORM_LABELS,
    )


@router.get("/stats")
async def stats_page():
    return render("stats.html", path="/stats", stats=await checks.stats())


@router.get("/about")
async def about():
    return render("about.html", path="/about")


# Bookmarks from the pre-Robyn site: the old package checker and home page.
_MOVED = {
    "/pypi": "/check",
    "/pypi/index": "/",
    "/pypi/check": "/check",
    "/pypi/list": "/stats",
    "/pages/index": "/",
    "/pages/about": "/about",
}


def _redirect_to(source: str, target: str):
    async def redirect():
        return Response(
            status_code=301, headers=Headers({"Location": target}), description=""
        )

    # Robyn names OpenAPI operations after the handler; keep them distinct.
    redirect.__name__ = "moved" + source.replace("/", "_")
    return redirect


for _old, _new in _MOVED.items():
    router.get(_old)(_redirect_to(_old, _new))
