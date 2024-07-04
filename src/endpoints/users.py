# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from dsg_lib.common_functions.email_validation import validate_email_address
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_sso.sso.github import GithubSSO
from loguru import logger
from sqlalchemy import Select

from ..db_tables import JobApplications, Notes, Users
from ..functions.date_functions import TIMEZONES as timezones
from ..functions.hash_function import hash_password, verify_password
from ..functions.login_required import check_login
from ..functions.models import RoleEnum
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


@router.get("/edit-user", response_class=HTMLResponse)
async def edit_user(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_identifier)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()

    context = {"page": "user", "user": user, "timezones": timezones}

    response = templates.TemplateResponse(
        request=request, name="/users/user_edit.html", context=context
    )

    return response


@router.post("/edit-user")
async def edit_user_post(
    request: Request,
    user_info: dict = Depends(check_login),
):
    request.session.pop("error-message", None)
    form = await request.form()

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    errors = []

    first_name = form["first_name"]
    if len(first_name) < 2:
        errors.append("First name is too short")

    last_name = form["last_name"]
    if len(last_name) < 2:
        errors.append("Last name is too short")

    email = form["email"]

    email_validation = validate_email_address(email, check_deliverability=True)

    if email_validation["valid"] is False:
        errors.append(email_validation["error"])

    user_timezone = form["my_timezone"]
    if user_timezone not in timezones:
        errors.append("Invalid timezone")

    if errors:
        request.session["error-message"] = errors
        return RedirectResponse(url="/users/edit-user", status_code=303)

    update = await db_ops.update_one(
        table=Users,
        new_values={
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "my_timezone": user_timezone,
        },
        record_id=user_identifier,
    )
    if user_timezone != user_info["timezone"]:
        request.session["timezone"] = user_timezone
    message = "User updated successfully"

    logger.debug(f"User update: {update}")
    request.session["message"] = message

    response = RedirectResponse(url="/users/user-info", status_code=303)
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
    user_info: dict = Depends(check_login),
    error: str = None,
):
    context = {"page": "user", "error": error}
    response = templates.TemplateResponse(
        request=request, name="users/password_change.html", context=context
    )
    return response


@router.post("/password-change")
async def post_password_change_form(
    request: Request,
    user_info: dict = Depends(check_login),
):
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
            request=request,
            name="users/error_message.html",
            context={"error": request.session["error"]},
        )
    if new_password != new_password_confirm:
        request.session["error"] = "New passwords do not match"
        return templates.TemplateResponse(
            request=request,
            name="users/error_message.html",
            context={"error": request.session["error"]},
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
        request=request,
        name="users/message.html",
        context={"message": request.session["message"]},
    )


# get user information endpoint
@router.get("/user-info", response_class=HTMLResponse)
async def get_user_info(
    request: Request, message: dict = None, user_info: dict = Depends(check_login)
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

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
        "page": "user",
        "user": user,
        "notes_count": notes_count,
        "job_app_count": job_app_count,
        "message": message,
    }
    return templates.TemplateResponse(
        request=request, name="/users/user_info.html", context=context
    )


github_sso = GithubSSO(
    settings.github_client_id,
    settings.github_client_secret.get_secret_value(),
    f"{settings.github_call_back_domain}/users/callback",
)


@router.get("/github-login")
async def github_login():
    with github_sso:
        return await github_sso.get_login_redirect()


@router.get("/callback")
async def github_callback(request: Request):

    with github_sso:
        user = await github_sso.verify_and_process(request)

    user_stored = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user.display_name)
    )

    if not user_stored:
        is_admin = False
        is_active = False
        if settings.admin_user.get_secret_value().lower() == user.display_name.lower():
            is_admin = True
            is_active = True
            add_roles = {}
            for role in RoleEnum:
                add_roles[role] = True
        else:
            add_roles = {"user_access": True}
        new_user = Users(
            user_name=user.display_name,
            email=user.email,
            my_timezone=settings.default_timezone,
            is_active=is_active,
            is_admin=is_admin,
            roles=add_roles,
        )
        user_stored = await db_ops.create_one(new_user)
        logger.debug(user_stored)

    try:
        user_stored = user_stored.to_dict()
        # Log the successful login attempt
        logger.info(f"Successful login attempt for user {user_stored}")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred: {e}")

    # Set the user identifier in the session
    request.session["user_identifier"] = user_stored["pkid"]
    request.session["roles"] = user_stored["roles"]
    request.session["is_active"] = user_stored["is_active"]
    if user_stored["is_admin"] is True:
        request.session["is_admin"] = True
    request.session["timezone"] = user_stored["my_timezone"]

    # Set the session expiration time
    session_duration = timedelta(minutes=settings.max_age)
    expiration_time = datetime.now() + session_duration
    request.session["exp"] = expiration_time.timestamp()

    # Create the response object

    # Update the last login date and reset the failed login attempts in the database
    login_update = await db_ops.update_one(
        table=Users,
        new_values={
            "date_last_login": datetime.utcnow(),
            "failed_login_attempts": 0,
        },
        record_id=user_stored["pkid"],
    )
    logger.debug(f"Login update: {login_update}")

    if user_stored["first_name"] is None or user_stored["last_name"] is None:
        response = RedirectResponse(
            url="/users/edit-user", status_code=status.HTTP_302_FOUND
        )
    else:
        # response.set_cookie(SESSION_COOKIE_NAME, access_token)
        response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    return response


# async def github_callback(request: Request, db: Session = Depends(get_db)):
#     """Process login response from GitHub and return user info"""

#     try:
#         with github_sso:
#             user = await github_sso.verify_and_process(request)
#         username = user.email if user.email else user.display_name
#         user_stored = db_crud.get_user(db, username, user.provider)
#         if not user_stored:
#             user_to_add = UserSignUp(
#                 username=username,
#                 fullname=user.display_name
#             )
#             user_stored = db_crud.add_user(
#                 db,
#                 user_to_add,
#                 provider=user.provider
#             )
#         access_token = create_access_token(
#             username=user_stored.username,
#             provider=user.provider
#         )
#         response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
#         response.set_cookie(SESSION_COOKIE_NAME, access_token)
#         return response
#     except db_crud.DuplicateError as e:
#         raise HTTPException(status_code=403, detail=f"{e}")
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=f"{e}")
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"An unexpected error occurred. Report this message to support: {e}"
#         )


# deactivate user endpoint

# delete user endpoint

# get user endpoint

# user metrics endpoint

# users metricts endpoint
