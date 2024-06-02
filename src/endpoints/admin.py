# -*- coding: utf-8 -*-
import secrets
from datetime import datetime

from dsg_lib.common_functions.email_validation import validate_email_address
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select

from ..db_tables import FailedLoginAttempts, JobApplications, Notes, Users
from ..functions import date_functions
from ..functions.hash_function import check_password_complexity, hash_password
from ..functions.login_required import check_login
from ..functions.models import RoleEnum
from ..resources import db_ops, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    user_info["is_admin"]

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
        for k, _v in user.items():
            if k.startswith("date_"):
                user[k] = await date_functions.timezone_update(
                    user_timezone=user_timezone,
                    date_time=user[k],
                    friendly_string=True,
                )

    return users


@router.get("/user/{user_id}", response_class=HTMLResponse)
async def admin_user(
    request: Request,
    user_id: str,
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_id)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()
    for k, _v in user.items():
        if k.startswith("date_"):
            user[k] = await date_functions.timezone_update(
                user_timezone=user_timezone,
                date_time=user[k],
                friendly_string=True,
            )

    notes_query = Select(Notes).where(Notes.user_id == user_id)
    notes_count = await db_ops.count_query(query=notes_query)

    job_app_query = Select(JobApplications).where(JobApplications.user_id == user_id)
    job_app_count = await db_ops.count_query(query=job_app_query)

    context = {
        "user": user,
        "notes_count": notes_count,
        "job_app_count": job_app_count,
        "random_pass": secrets.token_urlsafe(10),
        "roles": [
            role.value for role in sorted(RoleEnum, key=lambda x: x.name)
        ],  # List of all role values from the Enum, sorted by name
    }
    response = templates.TemplateResponse(
        request=request, name="/admin/user.html", context=context
    )

    return response


@router.post("/user/{update_user_id}", response_class=HTMLResponse)
async def admin_update_user(
    request: Request,
    update_user_id: str,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    if update_user_id == user_identifier:
        return Response(headers={"HX-Redirect": "/error/422"}, status_code=200)

    form = await request.form()

    account_action = form.get("account-action")

    if account_action == "delete":
        data = await db_ops.delete_one(table=Users, record_id=update_user_id)
        logger.info(f"User {update_user_id} deleted by {user_identifier}")
        logger.debug(f"data: {data}")
        data_notes = await db_ops.read_query(
            query=Select(Notes).where(Notes.user_id == update_user_id)
        )
        if data_notes is not None:
            logger.warning(f"No post found with ID: {update_user_id}")
            return RedirectResponse(url="/error/404", status_code=303)
        response = Response(
            headers={"HX-Redirect": "/admin/#access-tab"}, status_code=200
        )

        return response

    new_values = {}

    new_password = form.get("new-password-entry")

    is_complex = check_password_complexity(password=new_password)
    if is_complex == False:
        return Response(headers={"HX-Redirect": "/error/400"}, status_code=200)

    change_email_entry = form.get("change-email-entry")

    if account_action == "lock":
        new_values["is_locked"] = True

    elif new_password != "":
        hashed_password = hash_password(new_password)
        new_values["password"] = hashed_password

    elif change_email_entry != "":
        valid_email = validate_email_address(
            change_email_entry, check_deliverability=True
        )
        if valid_email["valid"]:
            new_values["email"] = change_email_entry
        else:
            return Response(headers={"HX-Redirect": "/error/400"}, status_code=200)

    data = await db_ops.update_one(
        table=Users, record_id=update_user_id, new_values=new_values
    )

    query = Select(Users).where(Users.pkid == update_user_id)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()

    response = Response(
        headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
    )

    return response


@router.post("/user/access/{update_user_id}", response_class=HTMLResponse)
async def admin_update_user_access(
    request: Request,
    update_user_id: str,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    is_admin = user_info["is_admin"]

    logger.debug(f"User {user_identifier} is admin: {is_admin}")

    if is_admin:
        form = await request.form()
        new_data = {}
        for key, value in form.items():
            role = key
            new_data[role] = value == "true"

        logger.debug(f"Form data: {new_data}")

        new_values = {
            "roles": new_data,
            "update_by": user_identifier,
            "date_updated": datetime.utcnow(),
        }

        logger.debug(f"Updating database with values: {new_values}")
        data = await db_ops.update_one(
            table=Users, record_id=update_user_id, new_values=new_values
        )
        logger.debug(f"Database update result: {data}")

        response = Response(
            headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
        )

        return response
    else:
        return Response(headers={"HX-Redirect": "/error/403"}, status_code=200)


@router.get("/failed-login-attempts", response_class=HTMLResponse)
async def admin_failed_login_attempts(
    request: Request,
    user_info: dict = Depends(check_login),
):
    """
    Handles the GET request for the "/failed-login-attempts" route.

    Args:
        request (Request): The incoming request.
        user_info (dict): The user information, obtained from the check_login dependency.

    Returns:
        TemplateResponse: The response, rendered using a template.
    """

    # Log the start of the process
    logger.info("Processing failed login attempts for admin")

    # Extract user identifier from user_info
    user_identifier = user_info["user_identifier"]

    # These lines don't seem to do anything. Consider removing them or using the values.
    user_info["timezone"]
    user_info["is_admin"]

    # Log the user identifier
    logger.debug(f"User identifier: {user_identifier}")

    # Create a query to select failed login attempts, limited to 1000
    query = Select(FailedLoginAttempts).limit(1000)

    # Execute the query and get the results
    failures = await db_ops.read_query(query=query)

    # Convert each failure to a dictionary
    failures = [fail.to_dict() for fail in failures]

    # Log the number of retrieved failed login attempts
    logger.debug(f"Retrieved {len(failures)} failed login attempts")

    # Create the context for the template
    context = {"user_identifier": user_identifier, "failures": failures}
    # Log the end of the process
    logger.info("Finished processing failed login attempts for admin")
    # Render the template and return the response
    return templates.TemplateResponse(
        request=request, name="/admin/failed_login_attempts.html", context=context
    )
