# -*- coding: utf-8 -*-


import re

from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from pydantic import (
    BaseModel,
    ValidationError,
    field_validator,
)
from sqlalchemy import Select

from ..db_tables import User
from ..functions.hash_function import verify_password
from ..resources import db_ops, templates

router = APIRouter()


class UserBase(BaseModel):
    first_name: str
    last_name: str
    user_name: str
    email: str
    password: str
    password2: str

    @field_validator("password1", check_fields=False)
    @classmethod
    def password_complexity(cls, password1):
        if len(password1) < 8:
            raise ValidationError("Password must be at least 8 characters long")
        if not re.search("[A-Z]", password1):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search("[a-z]", password1):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search("[0-9]", password1):
            raise ValidationError("Password must contain at least one number")
        if not re.search("[^A-Za-z0-9]", password1):
            raise ValidationError(
                "Password must contain at least one special character"
            )
        return password1

    @field_validator("password2", check_fields=False)
    def passwords_match(cls, password2, values, **kwargs):
        if "password1" in values and password2 != values["password1"]:
            raise ValidationError("passwords do not match")
        return password2


# create user endpoint
@router.post(
    "/users/create", response_model=UserBase, status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserBase):
    # The incoming data is validated by the UserBase model
    # If the data does not meet the validation requirements, a ValidationError will be raised
    user_data = UserBase(**user.dict())

    user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        user_name=user_data.user_name,
        email=user_data.email,
        password=user_data.password1,  # Use the validated password
    )
    logger.info(f"created_users: {user.user_name}")
    await db_ops.create_one(user)
    return user_data


# router login page
@router.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse("users/login.html", {"request": request})


# login user endpoint
@router.post("/login", status_code=status.HTTP_201_CREATED)
async def login_user(request: Request):
    login_attempt = request.session.get("login_attempt", 0)

    form = await request.form()
    data = dict(form)
    user_name = form["username"]
    password = form["password"]
    user = await db_ops.get_one_record(Select(User).where(User.user_name == user_name))
    toast_messages: list = [
        {"message": "User name not found or password is incorrect", "color": "alert"}
    ]

    if user is None or "error" in user:
        request.session["login_attempt"] = login_attempt + 1
        print(toast_messages)
        context = {"request": request, "toast_messages": toast_messages}
        return templates.TemplateResponse("toast-messages.html", context=context)
    if not verify_password(hash=user.password, password=password):
        request.session["login_attempt"] = login_attempt + 1
        context = {"request": request, "toast_messages": toast_messages}
        return templates.TemplateResponse("toast-messages.html", context=context)

    request.session["user_identifier"] = "abc123"
    return RedirectResponse(url="/", status_code=303)


# log out user endpoint

# update user endpoint

# update password endpoint

# deactivate user endpoint

# delete user endpoint

# get user endpoint

# get users endpoint

# user metrics endpoint

# users metricts endpoint
