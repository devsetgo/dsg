# -*- coding: utf-8 -*-
"""
This module contains the `require_login` decorator function.

The `require_login` function is a decorator that checks if a user is logged in and if the session is still valid before allowing access to an endpoint. If the user is not logged in or the session is not valid, it redirects to the login page.

This decorator should be used on all endpoints that require the user to be logged in.

Example:
    @app.get("/protected-endpoint")
    @require_login
    async def protected_endpoint():
        return {"message": "You are viewing a protected endpoint"}

This module depends on the `settings` module for configuration settings like the session user identifier and the login timeout.

This module uses the `loguru` library for logging.
"""
from datetime import datetime, timedelta
from typing import Callable

from fastapi import Request
from fastapi.responses import RedirectResponse, Response
from loguru import logger

from ..settings import settings


def require_login(endpoint: Callable) -> Callable:
    """
    This function is a decorator that checks if the user is logged in and if the session is still valid before allowing access to the endpoint.

    Args:
        endpoint (Callable): The endpoint function that this decorator is applied to.

    Returns:
        Callable: The decorated function that includes the login and session validity check.

    Raises:
        HTTPException: If the user is not logged in or if the session is not valid, it redirects to the login page.

    Example:
        @app.get("/protected-endpoint")
        @require_login
        async def protected_endpoint():
            return {"message": "You are viewing a protected endpoint"}

    Note:
        This decorator should be used on all endpoints that require the user to be logged in.
    """

    async def check_login(request: Request) -> Response:
        if not request.session.get(settings.sesson_user_identifier):
            logger.error(
                f"user page access without being logged in from {request.client.host}"
            )
            return RedirectResponse(url="/users/login", status_code=303)

        else:
            session_expiry_time = datetime.now() - timedelta(
                minutes=config_settings.login_timeout
            )
            try:
                last_updated = datetime.strptime(
                    request.session.get("updated", ""), "%Y-%m-%d %H:%M:%S.%f"
                )
            except ValueError:
                logger.error("Invalid session update time")
                return RedirectResponse(url="/users/login", status_code=303)

            current = session_expiry_time < last_updated

            if not current:
                logger.error(
                    f"user {request.session.get(settings.sesson_user_identifier)} outside window: {current}"
                )
                return RedirectResponse(url="/users/login", status_code=303)

            # update datetime of last use
            logger.info(
                f"user {request.session.get('id')} within timeout window: {current}"
            )
            request.session["updated"] = str(datetime.now())
        return await endpoint(request)

    return check_login
