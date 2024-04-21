# -*- coding: utf-8 -*-
import asyncio
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select

from ..db_tables import JobApplications, Notes, Users
from ..functions.hash_function import hash_password, verify_password
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings
from ..functions.validator import validate_email_address,timezones
router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login(request: Request, csrf_protect: CsrfProtect = Depends()):
    # Generate CSRF tokens
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    # Create template response with the generated CSRF token
    context = {"csrf_token": csrf_token}
    response = templates.TemplateResponse(
        request=request, name="users/login.html", context=context
    )

    # Set the signed CSRF token in the cookie
    csrf_protect.set_csrf_cookie(signed_token, response)

    logger.info(
        "Generated CSRF tokens, created template response, set CSRF cookie, and returning response."
    )

    return response


@router.post("/login")
async def login_user(request: Request, csrf_protect: CsrfProtect = Depends()):

    await asyncio.sleep(0.2)
    # Get the form data from the request
    form = await request.form()
    await csrf_protect.validate_csrf(request)
    user_name = form["username"]
    password = form["password"]

    # Log the login attempt
    logger.debug(f"Attempting to log in user: {user_name}")
    # Fetch the user record from the database
    user = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

    logger.debug(f"Users: {user}")
    # Check if the user exists and if they have made too many failed login attempts
    if (
        user is not None
        and user.failed_login_attempts >= settings.max_failed_login_attempts
    ):
        # Log the account lock
        logger.warning(
            f"Account for user: {user_name} is locked due to too many failed login attempts"
        )

        # Set the error message and return it in the response
        request.session["error"] = (
            "Account is locked due to too many failed login attempts"
        )
        return templates.TemplateResponse(
            "users/error_message.html",
            {"request": request, "error": request.session["error"]},
        )

    # Check if the user exists and if the password is correct
    if user is None or not verify_password(hash=user.password, password=password):
        # If the user exists, increment the failed login attempts
        if user is not None:
            login_attempt = user.failed_login_attempts + 1
            await db_ops.update_one(
                table=Users,
                new_values={"failed_login_attempts": login_attempt},
                record_id=user.pkid,
            )

        # Log the failed login attempt
        logger.debug(f"Failed login attempt for user: {user_name}")

        # Set the error message and return it in the response
        request.session["error"] = "Username and/or Password is incorrect"
        return templates.TemplateResponse(
            "users/error_message.html",
            {"request": request, "error": request.session["error"]},
        )

    # If the login is successful
    else:
        # Log the successful login attempt
        logger.info(f"Successful login attempt for user {user_name}")

        # Set the user identifier in the session
        request.session["user_identifier"] = user.pkid
        if user.is_admin == True:
            request.session["is_admin"] = True
        request.session["timezone"] = user.my_timezone

        # Set the session expiration time
        session_duration = timedelta(minutes=settings.max_age)
        expiration_time = datetime.now() + session_duration
        request.session["exp"] = expiration_time.timestamp()

        # Create the response object
        response = Response(headers={"HX-Redirect": "/notes"}, status_code=200)

        # Update the last login date and reset the failed login attempts in the database
        login_update = await db_ops.update_one(
            table=Users,
            new_values={
                "date_last_login": datetime.utcnow(),
                "failed_login_attempts": 0,
            },
            record_id=user.pkid,
        )
        logger.debug(f"Login update: {login_update}")
        # Return the response
        return response


@router.get("/logout")
async def logout(request: Request):
    user_identifier = request.session.get("user_identifier", None)
    request.session.clear()
    logger.info(f"Users {user_identifier} logged out")
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/password-change", response_class=HTMLResponse)
async def get_password_change_form(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    user_info: dict = Depends(check_login),
    error: str = None,
):

    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    context = {"csrf_token": csrf_token, "error": error}
    response = templates.TemplateResponse(
        request=request, name="users/password_change.html", context=context
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@router.post("/password-change")
async def post_password_change_form(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    user_info: dict = Depends(check_login),
):
    await csrf_protect.validate_csrf(request)
    form = await request.form()
    old_password = form["old_password"]
    new_password = form["new_password"]
    new_password_confirm = form["new_password_confirm"]
    user_identifier = request.session.get("user_identifier", None)
    user = await db_ops.read_one_record(
        Select(Users).where(Users.pkid == user_identifier)
    )
    if not verify_password(hash=user.password, password=old_password):
        request.session["error"] = "Old password is incorrect"
        return templates.TemplateResponse(
            "users/error_message.html",
            {"request": request, "error": request.session["error"]},
        )
    if new_password != new_password_confirm:
        request.session["error"] = "New passwords do not match"
        return templates.TemplateResponse(
            "users/error_message.html",
            {"request": request, "error": request.session["error"]},
        )
    new_password_hash = hash_password(new_password)
    update = await db_ops.update_one(
        table=Users,
        new_values={"password": new_password_hash},
        record_id=user_identifier,
    )
    logger.debug(f"Password update: {update}")
    request.session["message"] = "Password updated successfully"
    return templates.TemplateResponse(
        "users/message.html",
        {"request": request, "message": request.session["message"]},
    )


# get user information endpoint
@router.get("/user-info", response_class=HTMLResponse)
async def get_user_info(
    request: Request, message: dict = None, user_info: dict = Depends(check_login)
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_identifier)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()

    notes_query = Select(Notes).where(Notes.user_id == user_identifier)
    notes_count = await db_ops.count_query(query=notes_query)

    job_app_query = Select(JobApplications).where(
        JobApplications.user_id == user_identifier
    )
    job_app_count = await db_ops.count_query(query=job_app_query)

    context = {
        "user": user,
        "notes_count": notes_count,
        "job_app_count": job_app_count,
        "message": message,
    }
    return templates.TemplateResponse(
        request=request, name="/users/user_info.html", context=context
    )


@router.get("/edit-user", response_class=HTMLResponse)
async def edit_user(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_identifier)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    context = {"user": user, "csrf_token": csrf_token,"timezones":timezones}
    return templates.TemplateResponse(
        request=request, name="/users/user_edit.html", context=context
    )


@router.post("/edit-user")
async def edit_user_post(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):
    await csrf_protect.validate_csrf(request)
    form = await request.form()
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    is_admin = user_info["is_admin"]

    first_name = form["first_name"]
    last_name = form["last_name"]
    email = form["email"]
    user_name = form["user_name"]
    is_admin = form["is_admin"]
    user_timezone = form["user_timezone"]

    update = await db_ops.update_one(
        table=Users,
        new_values={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "user_name": user_name,
            "is_admin": is_admin,
            "my_timezone": user_timezone,
        },
        record_id=user_identifier,
    )
    message = "User updated successfully"

    logger.debug(f"User update: {update}")
    request.session["message"] = message
    return RedirectResponse(url="/users/user-info", status_code=303)


# deactivate user endpoint

# delete user endpoint

# get user endpoint

# user metrics endpoint

# users metricts endpoint
