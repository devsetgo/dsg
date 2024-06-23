# -*- coding: utf-8 -*-
"""
login_required.py

This module provides functions for checking user identifiers and session expiry times.
It uses the SQLAlchemy library for database operations and the settings module for configuration.

Functions:
    check_user_identifier(request): Checks if the user identifier in the session is valid.
    check_session_expiry(request): Checks if the session has expired.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
from loguru import logger
from sqlalchemy import Select

from ..db_tables import Users
from ..resources import db_ops
from ..settings import settings


async def check_user_identifier(request):
    """
    Checks if the user identifier in the session is valid.

    Args:
        request: The request object containing the session data.

    Raises:
        HTTPException: If the user identifier is not found in the session or the user does not exist in the database.
    """
    # Get the user identifier from the session
    user_identifier = request.session.get("user_identifier")

    # If the user identifier is not found in the session, log an error and raise an exception
    if user_identifier is None:
        logger.error(
            f"user page access without being logged in from {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")
    else:
        # If the user identifier is found in the session, check if the user exists in the database
        query = Select(Users).where(Users.pkid == user_identifier)
        user = await db_ops.read_one_record(query=query)

        # If the user does not exist in the database, log an error and raise an exception
        if user is None:
            logger.error(f"User not found with ID: {user_identifier}")
            raise HTTPException(status_code=401, detail="Unauthorized")


async def check_session_expiry(request):
    """
    Checks if the session has expired.

    Args:
        request: The request object containing the session data.

    Raises:
        HTTPException: If the session has expired or the session update time is invalid.
    """
    # Calculate the session expiry time
    session_expiry_time = datetime.now() - timedelta(minutes=settings.max_age)

    # Try to get the session update time from the session
    try:
        last_updated = datetime.fromtimestamp(request.session.get("exp", 0))
    except ValueError:
        # If the session update time is invalid, log an error and raise an exception
        logger.error("Invalid session update time")
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Check if the session has expired
    current = session_expiry_time < last_updated

    # If the session has expired, log an error and raise an exception
    if not current:
        logger.error(
            f"user {request.session.get('user_identifier')} outside window: {current}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")


async def check_login(request: Request):
    """
    Checks if the user is logged in and if the session is valid.

    Args:
        request (Request): The request object containing the session data.

    Raises:
        HTTPException: If the user is not logged in or the session has expired.

    Returns:
        dict: A dictionary containing the user's information.
    """
    # Get the user's information from the session
    request.state.user_info = {
        "user_identifier": request.session.get("user_identifier", None),
        "timezone": request.session.get("timezone", None),
        "is_admin": request.session.get("is_admin", False) is True,
        "exp": request.session.get("exp", 0),
    }

    logger.debug(f"check login initial: {request.state.user_info}")
    url = request.url

    # If the URL contains "/admin", check if the user is an admin
    if "/admin" in url.path:
        if not request.session.get("is_admin"):
            # If the user is not an admin, log an error and raise an exception
            logger.error(
                f"user page access without being logged in from {request.client.host}"
            )
            raise HTTPException(status_code=401, detail="Unauthorized")
        else:
            # If the user is an admin, check if the session has expired
            await check_session_expiry(request)

    # Check if the user identifier is valid and if the session has expired
    await check_user_identifier(request)
    await check_session_expiry(request)

    logger.debug(f"check login return: {request.state.user_info}")

    # Return the user's information
    return request.state.user_info
