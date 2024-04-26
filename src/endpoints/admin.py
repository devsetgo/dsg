# -*- coding: utf-8 -*-

# from pytz import timezone, UTC
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import Select

from ..db_tables import JobApplications, Notes, Users
from ..functions import date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()


@router.get("/")
async def admin_dashboard(
    request: Request,
    user_info: dict = Depends(check_login),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    user_list = await get_list_of_users(user_timezone=user_timezone)

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


@router.get("/user/{user_id}")
async def admin_user(
    request: Request, user_id: str, user_info: dict = Depends(check_login)
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_id)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()

    notes_query = Select(Notes).where(Notes.user_id == user_id)
    notes_count = await db_ops.count_query(query=notes_query)

    job_app_query = Select(JobApplications).where(JobApplications.user_id == user_id)
    job_app_count = await db_ops.count_query(query=job_app_query)

    context = {"user": user, "notes_count": notes_count, "job_app_count": job_app_count}
    return templates.TemplateResponse(
        request=request, name="/admin/user.html", context=context
    )
