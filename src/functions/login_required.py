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

from ..settings import settings

# def require_login(endpoint: Callable) -> Callable:
#     """
#     This function is a decorator that checks if the user is logged in and if the session is still valid before allowing access to the endpoint.

#     Args:
#         endpoint (Callable): The endpoint function that this decorator is applied to.

#     Returns:
#         Callable: The decorated function that includes the login and session validity check.

#     Raises:
#         HTTPException: If the user is not logged in or if the session is not valid, it redirects to the login page.

#     Example:
#         @require_login
#         @app.get("/protected-endpoint")
#         async def protected_endpoint(request: Request):
#             user_info = request.state.user_info
#             return {"message": f"You are viewing a protected endpoint, {user_info['user_identifier']}"}

#     Note:
#         This decorator should be used on all endpoints that require the user to be logged in.
#     """

#     async def check_login(request: Request) -> Response:
#         # Add user information to the request object

#         request.state.user_info = {
#             "user_identifier": request.session.get("user_identifier", None),
#             "timezone": request.session.get("timezone", None),
#             "is_admin": request.session.get("is_admin", False) is True,
#             "exp": request.session.get("exp", 0),
#         }

#         logger.debug(f"check login initial: {request.state.user_info}")
#         # Check if the user is logged in
#         if not request.session.get("user_identifier"):
#             # Log an error message and redirect to the login page
#             logger.error(
#                 f"user page access without being logged in from {request.client.host}"
#             )
#             return RedirectResponse(url="/users/login", status_code=303)
#         else:
#             # Calculate the session expiry time
#             session_expiry_time = datetime.now() - timedelta(minutes=settings.max_age)

#             try:
#                 # Convert the session expiry time to a datetime object
#                 last_updated = datetime.fromtimestamp(request.session.get("exp", 0))
#             except ValueError:
#                 # Log an error message and redirect to the login page
#                 logger.error("Invalid session update time")
#                 return RedirectResponse(url="/users/login", status_code=303)

#             # Check if the session is still valid
#             current = session_expiry_time < last_updated

#             if not current:
#                 # Log an error message and redirect to the login page
#                 logger.error(
#                     f"user {request.session.get('user_identifier')} outside window: {current}"
#                 )
#                 return RedirectResponse(url="/users/login", status_code=303)

#         # If the user is logged in and the session is valid, proceed to the endpoint
#         logger.critical(f"check login return: {request.state.user_info}")
#         return await endpoint(request)

#     # Return the decorated function
#     return check_login


def check_user_identifier(request):
    if request.session.get("user_identifier") is None:
        logger.error(
            f"user page access without being logged in from {request.client.host}"
        )
        raise HTTPException(status_code=401, detail="Unauthorized")


def check_session_expiry(request):
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

    check_user_identifier(request)
    check_session_expiry(request)

    logger.critical(f"check login return: {request.state.user_info}")
    return request.state.user_info
