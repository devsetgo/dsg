# -*- coding: utf-8 -*-


from datetime import datetime
from typing import List
from loguru import logger
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator
from sqlalchemy import Delete, Insert, Select, Update
import re
from ..functions.hash_function import hash_password, verify_password, check_needs_rehash


from ..resources import db_ops
from ..db_tables import User


router = APIRouter()


class UserBase(BaseModel):
    first_name: str
    last_name: str
    user_name: str
    email: str
    password: str
    password2: str

    @validator("password1")
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

    @validator("password2")
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


# login user endpoint
@router.post("/login", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def login_user(user, password):
    user = await db_ops.get_one(Select(User).where(User.user_name == user))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(user.password, password):
        raise HTTPException(status_code=400, detail="Incorrect password")
    return user


# log out user endpoint

# update user endpoint

# update password endpoint

# deactivate user endpoint

# delete user endpoint

# get user endpoint

# get users endpoint

# user metrics endpoint

# users metricts endpoint
