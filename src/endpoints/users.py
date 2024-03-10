# -*- coding: utf-8 -*-
import re
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator
from sqlalchemy import Select

from ..db_tables import User
from ..functions.hash_function import verify_password
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


# router login page
@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    user_identifier = request.session.get("user_identifier", None)
    if user_identifier is not None:
        return RedirectResponse(
            url="/pages/index", status_code=status.HTTP_303_SEE_OTHER
        )

    request.session["error"] = None
    return templates.TemplateResponse(
        request=request, name="users/login.html", context={}
    )


@router.post("/login")
async def login_user(request: Request):
    """
    Handle user login.

    This function handles the POST request for user login. It checks if the user exists and if the password is correct.
    If the user has made too many failed login attempts, it locks the account and returns an error message.
    If the login is successful, it updates the last login date and resets the failed login attempts.

    Args:
        request (Request): The incoming request object.

    Returns:
        TemplateResponse: A response object with the result of the login attempt.
    """
    # Get the form data from the request
    form = await request.form()
    user_name = form["username"]
    password = form["password"]

    # Log the login attempt
    logger.debug(f"Attempting to log in user: {user_name}")
    # Fetch the user record from the database
    user = await db_ops.read_one_record(Select(User).where(User.user_name == user_name))

    logger.debug(f"User: {user}")
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
                table=User,
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
        request.session["user_identifier"] = user.pkid
        request.session["timezone"] = user.my_timezone

        # Create the response object
        response = Response(headers={"HX-Redirect": "/"}, status_code=200)

        # Update the last login date and reset the failed login attempts in the database
        login_update = await db_ops.update_one(
            table=User,
            new_values={
                "date_last_login": datetime.utcnow(),
                "failed_login_attempts": 0,
            },
            record_id=user.pkid,
        )
        logger.debug(f"Login update: {login_update}")
        # Return the response
        return response


# log out user endpoint
@router.get("/logout")
async def logout(request: Request):
    request.session["user_identifier"] = None
    request.session["login_attempt"] = 0
    return RedirectResponse(url="/users/login", status_code=status.HTTP_303_SEE_OTHER)


# update user endpoint

# update password endpoint

# deactivate user endpoint

# delete user endpoint

# get user endpoint

# get users endpoint

# user metrics endpoint

# users metricts endpoint

# class UserBase(BaseModel):
#     first_name: str
#     last_name: str
#     user_name: str
#     email: str
#     password: str
#     password2: str

#     @field_validator("password1", check_fields=False)
#     @classmethod
#     def password_complexity(cls, password1):
#         if len(password1) < 8:
#             raise ValidationError("Password must be at least 8 characters long")
#         if not re.search("[A-Z]", password1):
#             raise ValidationError("Password must contain at least one uppercase letter")
#         if not re.search("[a-z]", password1):
#             raise ValidationError("Password must contain at least one lowercase letter")
#         if not re.search("[0-9]", password1):
#             raise ValidationError("Password must contain at least one number")
#         if not re.search("[^A-Za-z0-9]", password1):
#             raise ValidationError(
#                 "Password must contain at least one special character"
#             )
#         return password1

#     @field_validator("password2", check_fields=False)
#     def passwords_match(cls, password2, values, **kwargs):
#         if "password1" in values and password2 != values["password1"]:
#             raise ValidationError("passwords do not match")
#         return password2


# # create user endpoint
# @router.post(
#     "/users/create", response_model=UserBase, status_code=status.HTTP_201_CREATED
# )
# async def create_user(user: UserBase):
#     # The incoming data is validated by the UserBase model
#     # If the data does not meet the validation requirements, a ValidationError will be raised
#     user_data = UserBase(**user.dict())

#     user = User(
#         first_name=user_data.first_name,
#         last_name=user_data.last_name,
#         user_name=user_data.user_name,
#         email=user_data.email,
#         password=user_data.password1,  # Use the validated password
#     )
#     logger.info(f"created_users: {user.user_name}")
#     await db_ops.create_one(user)
#     return user_data
