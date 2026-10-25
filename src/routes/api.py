# -*- coding: utf-8 -*-
"""JSON endpoints: a scripting API for resolution. Framework-neutral: see
src/web.py. Health checks are per server (src/routes/health.py for Robyn,
src/rsgi.py for RSGI)."""

from loguru import logger

from .. import checks
from ..forms import PackageCheckForm
from ..web import Request, Reply, RouteTable, json_reply
from .pages import client_ip, submission_refusal

ROUTES = RouteTable()


@ROUTES.post("/api/check")
async def api_check(request: Request) -> Reply:
    """POST {"requirements": "...", "python_version": "3.12", "platform": "linux-x86_64", "mode": "upgrade"}.

    Resolves synchronously and returns the report; the check is also stored so
    it shows up at /check/<request_group_id>.
    """
    try:
        body = request.json()
    except ValueError, TypeError:
        return json_reply({"error": "Body must be a JSON object."}, 400)
    if not isinstance(body, dict):
        return json_reply({"error": "Body must be a JSON object."}, 400)
    result = PackageCheckForm.validate(body, submit_url="/api/check")
    if not result.is_valid:
        return json_reply(
            {"error": "Invalid request.", "errors": result.error_list()}, 422
        )
    form = result.instance

    refusal = submission_refusal(request)
    if refusal is not None:
        return json_reply({"error": refusal}, 429)

    try:
        request_group_id = await checks.create_check(
            requirements=form.requirements,
            python_version=form.python_version,
            platform=form.platform,
            mode=form.mode,
            host_ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except BaseException as exc:
        # Every way out of here gives the reserved queue place back, a
        # cancelled request (CancelledError is not an Exception) included.
        checks.release_reservation()
        if not isinstance(exc, Exception):
            raise
        # A JSON caller gets JSON, not the HTML error page; the detail
        # (SQL, paths) stays in the log.
        logger.exception("could not store an API check")
        return json_reply(
            {"error": "An internal error stopped this check. It has been logged."},
            500,
        )
    # The same path as the web form (slot, heartbeat, redaction, error
    # handling), just awaited instead of polled.
    await checks.run_check(request_group_id, reserved=True)
    check = await checks.get_check(request_group_id)
    url = f"/check/{request_group_id}"
    if check is None or not check.report:
        error = (check.error if check else None) or "The check did not complete."
        return json_reply(
            {"error": error, "request_group_id": request_group_id, "url": url}, 502
        )
    payload = dict(check.report)
    payload["request_group_id"] = request_group_id
    payload["url"] = url
    return json_reply(payload, 200 if payload.get("ok") else 409)
