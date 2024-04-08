# # -*- coding: utf-8 -*-

# from typing import Dict, Optional, Union

# from fastapi import HTTPException, Request
# from loguru import logger


# def get_user_info(request: Request) -> Dict[str, Optional[Union[str, bool]]]:
#     """
#     Retrieves user information from the session.

#     Args:
#         request (Request): The request object containing the session.

#     Returns:
#         Dict[str, Optional[Union[str, bool]]]: A dictionary containing the user identifier, timezone, and admin status.

#     Raises:
#         HTTPException: If the user identifier is None, it raises an HTTPException to redirect to the login page.
#     """
#     # Retrieve user information from the session
#     print(request.session)
#     user_info = {
#         "user_identifier": request.session.get("user_identifier", None),
#         "user_timezone": request.session.get("timezone", None),
#         "is_admin": request.session.get("is_admin", False) is True,
#     }

#     # If the user identifier is None, log the event and redirect to the login page
#     if user_info["user_identifier"] is None:
#         logger.info(
#             "User identifier is None, redirecting to login",
#             extra={
#                 "url": request.url,
#                 "headers": request.headers,
#             },
#         )
#         raise HTTPException(status_code=303, headers={"Location": "/users/login"})

#     # Log the user information
#     logger.debug(
#         "User info",
#         extra={
#             "user_identifier": user_info["user_identifier"],
#             "user_timezone": user_info["user_timezone"],
#             "is_admin": user_info["is_admin"],
#             "headers": request.headers,
#         },
#     )

#     # Return the user information
#     return user_info
