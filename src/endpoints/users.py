# -*- coding: utf-8 -*-


from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import Delete, Insert, Select, Update

from .resources import db_ops


class UserBase(BaseModel):
    name_first: str = Field(
        ...,
        # alias="firstName",
        description="the users first or given name",
        examples=["Bob"],
    )
    name_last: str = Field(
        ...,
        # alias="lastName",
        description="the users last or surname name",
        examples=["Fruit"],
    )
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    _id: str
    date_created: datetime
    date_updated: datetime

    model_config = ConfigDict(from_attributes=True)


class UserList(BaseModel):
    users: List[UserBase]


router = APIRouter()


@router.get("/users/count")
async def count_users():
    count = await DatabaseOperations.count_query(Select(User))
    return {"count": count}


@router.get("/users")
async def read_users(
    limit: int = Query(None, alias="limit", ge=1, le=1000),
    offset: int = Query(None, alias="offset"),
):
    if limit is None:
        limit = 500

    if offset is None:
        offset = 0

    query_count = Select(User)
    total_count = await DatabaseOperations.count_query(query=query_count)
    query = Select(User)
    users = await DatabaseOperations.fetch_query(
        query=query, limit=limit, offset=offset
    )
    return {
        "query_data": {"total_count": total_count, "count": len(users)},
        "users": users,
    }


@router.post(
    "/users/", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def create_user(user: UserBase):
    db_user = User(
        name_first=user.name_first, name_last=user.name_last, email=user.email
    )
    created_user = await DatabaseOperations.execute_one(db_user)
    return created_user


@router.post(
    "/users/bulk/",
    response_model=List[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_users(user_list: UserList):
    db_users = [
        User(name_first=user.name_first, name_last=user.name_last, email=user.email)
        for user in user_list.users
    ]
    created_users = await DatabaseOperations.execute_many(db_users)
    return created_users


import random
import string


@router.get(
    "/users/bulk/auto",
    response_model=List[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_users_auto(qty: int = Query(100, le=1000, ge=1)):
    created_users: list = []
    for i in range(qty):
        # Generate a random first name, last name
        name_first = "".join(random.choices(string.ascii_lowercase, k=5))
        name_last = "".join(random.choices(string.ascii_lowercase, k=5))

        # Generate a random email
        random_email_part = "".join(
            random.choices(string.ascii_lowercase + string.digits, k=10)
        )
        email = f"user{random_email_part}@yahoo.com"

        db_user = User(name_first=name_first, name_last=name_last, email=email)
        created_user = await DatabaseOperations.execute_one(db_user)
        created_users.append(created_user)

    return created_users


@router.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: str):
    users = await DatabaseOperations.fetch_query(
        Select(User).where(User._id == user_id)
    )
    if not users:
        raise HTTPException(status_code=404, detail="User not found")
    return users[0]
