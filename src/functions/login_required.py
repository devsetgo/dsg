# -*- coding: utf-8 -*-
"""
This module contains the `require_login` decorator function.

The `require_login` function is a decorator that checks if a user is logged in and if the session is still valid before allowing access to an endpoint. If the user is not logged in or the session is not valid, it redirects to the login page.

This decorator should be used on all endpoints that require the user to be logged in.

Example:
    @require_login
    @app.get("/protected-endpoint")
    async def protected_endpoint(request: Request):
        user_info = request.state.user_info
        return {"message": f"You are viewing a protected endpoint, {user_info['user_identifier']}"}

This module depends on the `settings` module for configuration settings like the session user identifier and the login timeout.

This module uses the `loguru` library for logging.

The order of decorators matters. The decorator closest to the function (i.e., the one at the bottom) is applied first, then the one above it, and so on. Therefore, when using this decorator with others (like route decorators), make sure to place it above the route decorator to ensure the `require_login` function is called after the routing function, allowing any dependencies injected by the routing function to be available within `require_login`.

Example:
    @require_login
    @app.get("/protected-endpoint")
    async def protected_endpoint():
        return {"message": "You are viewing a protected endpoint"}
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from loguru import logger
from ..resources import db_ops
from ..db_tables import Categories, Posts, Users
from sqlalchemy import Select, Text, and_, asc, cast, or_
from ..settings import settings


async def check_user_identifier(request):
    user_identifier = request.session.get("user_identifier")
    
    if user_identifier is None:
        logger.error(
            f"user page access without being logged in from {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        query = Select(Users).where(Users.pkid == user_identifier)
        user = await db_ops.read_one_record(query=query)
        if user is None:
            logger.error(f"User not found with ID: {user_identifier}")
            
            raise HTTPException(status_code=401, detail="Unauthorized")



async def check_session_expiry(request):
    session_expiry_time = datetime.now() - timedelta(minutes=settings.max_age)
    try:
        last_updated = datetime.fromtimestamp(request.session.get("exp", 0))
    except ValueError:
        logger.error("Invalid session update time")
        raise HTTPException(status_code=401, detail="Unauthorized")

    current = session_expiry_time < last_updated

    if not current:
        logger.error(
            f"user {request.session.get('user_identifier')} outside window: {current}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")


async def check_login(request: Request):
    request.state.user_info = {
        "user_identifier": request.session.get("user_identifier", None),
        "timezone": request.session.get("timezone", None),
        "is_admin": request.session.get("is_admin", False) is True,
        "exp": request.session.get("exp", 0),
    }

    logger.debug(f"check login initial: {request.state.user_info}")
    url = request.url

    # if url contains "/admin" then check if user is admin
    if "/admin" in url.path:
        if not request.session.get("is_admin"):
            logger.error(
                f"user page access without being logged in from {request.client.host}"
            )
            raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            check_session_expiry(request)

    await check_user_identifier(request)
    await check_session_expiry(request)

    logger.debug(f"check login return: {request.state.user_info}")
    return request.state.user_info
