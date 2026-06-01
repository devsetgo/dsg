# -*- coding: utf-8 -*-
from datetime import timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from loguru import logger
from sqlalchemy import Select

from ..db_tables import Notifications
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()


def _format_notifications(results, user_timezone: str) -> list:
    tz = ZoneInfo(user_timezone)
    out = []
    for n in results:
        d = n.to_dict()
        if d.get("date_created"):
            # Stored as naive UTC — localize before converting to user timezone
            dt = d["date_created"].replace(tzinfo=timezone.utc)
            d["date_created"] = dt.astimezone(tz).strftime("%b %d %H:%M")
        out.append(d)
    return out


def _is_valid_result(result) -> bool:
    """Return True only for real ORM objects, not None or dsg_lib error dicts."""
    return result is not None and not isinstance(result, dict)


async def _render_item(request: Request, notification_id: str, user_timezone: str, user_identifier: str) -> tuple:
    """Re-fetch a notification (with ownership) and format it for rendering."""
    result = await db_ops.read_one_record(
        query=Select(Notifications).where(
            Notifications.pkid == notification_id,
            Notifications.user_id == user_identifier,
        )
    )
    n = _format_notifications([result], user_timezone)[0] if _is_valid_result(result) else None
    return n


@router.get("/partial", response_class=HTMLResponse)
async def notifications_partial(
    request: Request,
    show_all: bool = Query(False),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info.get("timezone", "UTC")

    query = Select(Notifications).where(Notifications.user_id == user_identifier)
    if not show_all:
        query = query.where(Notifications.is_read == False)  # noqa: E712
    if show_all:
        query = query.order_by(Notifications.is_read.asc(), Notifications.date_created.desc())
    else:
        query = query.order_by(Notifications.date_created.desc())
    query = query.limit(50)

    results = await db_ops.read_query(query=query)
    notifications = _format_notifications(
        results if results and not isinstance(results, str) else [],
        user_timezone,
    )

    return templates.TemplateResponse(
        request=request,
        name="notifications/items.html",
        context={"notifications": notifications, "show_all": show_all},
    )


@router.get("/badge", response_class=HTMLResponse)
async def notifications_badge(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    query = Select(Notifications).where(
        Notifications.user_id == user_identifier,
        Notifications.is_read == False,  # noqa: E712
    )
    count = await db_ops.count_query(query=query)
    return templates.TemplateResponse(
        request=request,
        name="notifications/badge.html",
        context={"count": count},
    )


@router.post("/{notification_id}/read", response_class=HTMLResponse)
async def mark_notification_read(
    request: Request,
    notification_id: str,
    show_all: bool = Query(False),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info.get("timezone", "UTC")

    # Ownership check before update
    existing = await db_ops.read_one_record(
        query=Select(Notifications).where(
            Notifications.pkid == notification_id,
            Notifications.user_id == user_identifier,
        )
    )
    if not _is_valid_result(existing):
        return HTMLResponse("", status_code=404)

    await db_ops.update_one(
        table=Notifications,
        record_id=notification_id,
        new_values={"is_read": True},
    )
    logger.debug(f"Marked notification {notification_id} read for user {user_identifier}")

    if not show_all:
        return HTMLResponse("")

    n = await _render_item(request, notification_id, user_timezone, user_identifier)
    return templates.TemplateResponse(
        request=request,
        name="notifications/item.html",
        context={"n": n, "show_all": True},
    )


@router.post("/{notification_id}/unread", response_class=HTMLResponse)
async def mark_notification_unread(
    request: Request,
    notification_id: str,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info.get("timezone", "UTC")

    # Ownership check before update
    existing = await db_ops.read_one_record(
        query=Select(Notifications).where(
            Notifications.pkid == notification_id,
            Notifications.user_id == user_identifier,
        )
    )
    if not _is_valid_result(existing):
        return HTMLResponse("", status_code=404)

    await db_ops.update_one(
        table=Notifications,
        record_id=notification_id,
        new_values={"is_read": False},
    )
    logger.debug(f"Marked notification {notification_id} unread for user {user_identifier}")

    n = await _render_item(request, notification_id, user_timezone, user_identifier)
    return templates.TemplateResponse(
        request=request,
        name="notifications/item.html",
        context={"n": n, "show_all": True},
    )


@router.delete("/clear-all", response_class=HTMLResponse)
async def clear_all_notifications(
    request: Request,
    show_all: bool = Query(False),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    query = Select(Notifications).where(Notifications.user_id == user_identifier)
    results = await db_ops.read_query(query=query)
    if results and not isinstance(results, str):
        for n in results:
            await db_ops.delete_one(table=Notifications, record_id=n.pkid)
    logger.info(f"Cleared all notifications for user {user_identifier}")
    return templates.TemplateResponse(
        request=request,
        name="notifications/items.html",
        context={"notifications": [], "show_all": show_all},
    )
