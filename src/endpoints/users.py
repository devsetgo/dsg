# -*- coding: utf-8 -*-
import re

from fastapi import APIRouter, Request, status, HTTPException,Response
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
)
from sqlalchemy import Select
from fastapi_csrf_protect import CsrfProtect
from ..db_tables import User
from ..functions.hash_function import verify_password
from ..resources import db_ops, templates

router = APIRouter()



# router login page
@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    user_identifier = request.session.get("user_identifier", None)
    print(user_identifier)
    if user_identifier is not None:
        return RedirectResponse(url="/pages/index", status_code=status.HTTP_303_SEE_OTHER)
    
    request.session["error"] = None
    return templates.TemplateResponse(
        request=request, name="users/login.html", context={}
    )


# login user endpoint
@router.post("/login")
async def login_user(request: Request):
    login_attempt = request.session.get("login_attempt", 0)

    
    form = await request.form()
    user_name = form['username']
    password = form['password']
    print(user_name,password)
    user = await db_ops.read_one_record(Select(User).where(User.user_name == user_name))
    logger.debug(user.__dict__)
    # result = verify_password(hash=user.password, password=password)
    
    if user is None or not verify_password(hash=user.password, password=password):
        login_attempt += 1
        request.session["login_attempt"] = login_attempt
        logger.error(f"Failed login attempt {login_attempt} for user {user_name}")
        request.session["error"] = "User name not found or password is incorrect"
        return templates.TemplateResponse(
            "users/error_message.html", {"request": request, "error": request.session["error"]}
        )
    else:
        logger.info(f"Successful login attempt for user {user_name}")
        request.session["user_identifier"] = user.pkid
        request.session['login_attempt'] = 0
        response = Response(headers={"HX-Redirect": "/"}, status_code=200)
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
