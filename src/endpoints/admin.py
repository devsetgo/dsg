# -*- coding: utf-8 -*-

# from pytz import timezone, UTC
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select

from ..db_tables import JobApplications, Notes, Users
from ..functions import date_functions
from ..functions.hash_function import hash_password
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
    request: Request,
    user_id: str,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
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
    # Generate CSRF tokens
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    context = {
        "user": user,
        "notes_count": notes_count,
        "job_app_count": job_app_count,
        "csrf_token": csrf_token,
    }
    response = templates.TemplateResponse(
        request=request, name="/admin/user.html", context=context
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post("/user/{update_user_id}")
async def admin_update_user(
    request: Request,
    update_user_id: str,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    await csrf_protect.validate_csrf(request)
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    if update_user_id == user_identifier:

        return Response(headers={"HX-Redirect": f"/error/422"}, status_code=200)

    form = await request.form()

    account_action = form.get("account-action")

    if account_action == "delete":
        print("delete")
        data = await db_ops.delete_one(table=Users, record_id=update_user_id)
        logger.info(f"User {update_user_id} deleted by {user_identifier}")
        logger.debug(f"data: {data}")
        data_notes =  await db_ops.read_query(query=Select(Notes).where(Notes.user_id == update_user_id))
        print(data_notes)
        response = Response(
            headers={"HX-Redirect": f"/admin/#access-tab"}, status_code=200
        )
        csrf_protect.unset_csrf_cookie(response)
        return response
    elif account_action == "lock":
        print("lock")
        data = await db_ops.update_one(
        table=Users,
        new_values={"is_locked": True},
        record_id=update_user_id,
    )
        print(data)
        logger.info(f"User {update_user_id} deleted by {user_identifier}")
        logger.debug(f"data: {data}")
        response = Response(
            headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
        )
        csrf_protect.unset_csrf_cookie(response)
        return response

    new_values = {}
    new_password = form.get("new-password-entry")
    if new_password != "":
        print(f"new password: {new_password}")
        new_values["password"] = new_password

    change_email_entry = form.get("change-email-entry")
    if change_email_entry != "":
        print(f"email: {change_email_entry}")
        new_values["email"] = change_email_entry

    query = Select(Users).where(Users.pkid == update_user_id)
    user = await db_ops.read_one_record(query=query)

    print(new_values)
    # update = await db_ops.update_one(
    #     table=Users,
    #     new_values={
    #         "first_name": first_name,
    #         "last_name": last_name,
    #         "email": email,
    #         "my_timezone": user_timezone,
    #     },
    #     record_id=user_identifier,
    # )

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()
    # context = {"request": request, "user": user, "user_id": update_user_id}
    # response = RedirectResponse(url=f"/admin/user/{update_user_id}", status_code=303)
    response = Response(
        headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
    )
    csrf_protect.unset_csrf_cookie(response)
    return response
