# -*- coding: utf-8 -*-
import time
import sys
# from debug_toolbar.middleware import DebugToolbarMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .settings import settings


def add_middleware(app):
    # app.add_middleware(
    #     DebugToolbarMiddleware,
    #     # panels=["debug_toolbar.panels.sqlalchemy.SQLAlchemyPanel"], # appears incompatible
    #     settings=[Settings()],
    # )
    # app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site=settings.same_site,
        https_only=settings.https_only,
        max_age=settings.max_age,
    )


    # Check if the application is being run with uvicorn
    if "uvicorn" in sys.argv[0]:
        app.add_middleware(
            AccessLoggerMiddleware, user_identifier=settings.session_user_identifier
        )
        logger.debug("AccessLoggerMiddleware added")
    else:
        logger.info("Surpressing AccessLoggerMiddleware as not running with uvicorn")


class AccessLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests made to application
    """

    def __init__(self, app, user_identifier: str = "id"):
        super().__init__(app)
        self.user_identifier = user_identifier

    async def dispatch(self, request, call_next):
        # Record the start time
        start_time = time.time()
        try:
            # Call the next middleware or endpoint in the stack
            response = await call_next(request)
            # Get the status code from the response
            status_code = response.status_code
            logger.debug(f"Response: {response}")
        except Exception as e:
            # Log the exception and re-raise it
            logger.exception(f"An error occurred while processing the request: {e}")
            raise

        # Calculate the processing time
        process_time = time.time() - start_time
        logger.debug(f"Processing time: {process_time}")

        # Get the request details
        method = request.method
        url = request.url
        client = request.client.host
        referer = request.headers.get("referer", "No referer")
        user_id = request.session.get(self.user_identifier, "unknown guest")
        headers = dict(request.headers.items())
        sensitive_headers = ["Authorization"]

        # Redact sensitive headers
        for header in sensitive_headers:
            if header in headers:
                headers[header] = "[REDACTED]"

        # Log the request details, but ignore favicon.ico requests
        if url.path != "/favicon.ico":
            logger.info(
                {
                    "method": method,
                    "url": str(url),
                    "client": client,
                    "referer": referer,
                    "user_id": user_id,
                    "headers": headers,
                    "status_code": status_code,
                    "process_time": process_time,
                }
            )

        # Return the response
        return response