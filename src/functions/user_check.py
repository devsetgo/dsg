# -*- coding: utf-8 -*-

from fastapi import HTTPException, Request
from loguru import logger


def get_user_info(request: Request):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    is_admin = request.session.get("is_admin", None)

    if user_identifier is None:
        logger.info(
            f"User identifier is None, redirecting to login: {request.url} - {request.headers}"
        )
        raise HTTPException(status_code=303, headers={"Location": "/users/login"})

    logger.debug(
        f"User: {user_identifier}, Timezone: {user_timezone}, Admin: {is_admin}, Headers: {request.headers}"
    )
    return user_identifier, user_timezone, is_admin
