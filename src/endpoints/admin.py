# -*- coding: utf-8 -*-
import csv
import io
from datetime import UTC, datetime, timedelta
import re

# from pytz import timezone, UTC
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pytz import timezone
from sqlalchemy import Select, Text, and_, between, cast, extract, or_, text

from ..db_tables import Notes, Users
from ..functions import ai, date_functions, note_import, notes_metrics
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


@router.get("/")
async def admin_dashboard(
    request: Request,
    user_info: dict = Depends(check_login),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    user_list =  await get_list_of_users(user_timezone=user_timezone)

    context = {"user_identifier": user_identifier, "users": user_list}
    return templates.TemplateResponse(
        request=request, name="/admin/dashboard.html", context=context
    )

async def get_list_of_users(user_timezone: str):
    query = Select(Users)
    users = await db_ops.read_query(query=query)
    users = [user.to_dict() for user in users]
    for user in users:

        user["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=user["date_created"],
            friendly_string=True,
        )
        user["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=user["date_updated"],
            friendly_string=True,
        )

    return users
