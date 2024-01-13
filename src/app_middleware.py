# -*- coding: utf-8 -*-
import time

from fastapi.middleware.gzip import GZipMiddleware
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .settings import settings


def add_middleware(app):
    # app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret_key,
        same_site=settings.same_site,
        https_only=settings.https_only,
        max_age=settings.max_age,
    )
    app.add_middleware(AccessLoggerMiddleware, user_identifier="id")


# needs for middleware to be added
# csrf protection


class AccessLoggerMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests made to application
    """

    def __init__(self, app, user_identifier: str = "id"):
        super().__init__(app)
        self.user_identifier = user_identifier

    async def dispatch(self, request, call_next):
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.exception(f"An error occurred while processing the request: {e}")
            raise

        process_time = time.time() - start_time
        method = request.method
        url = request.url
        client = request.client.host
        referer = request.headers.get("referer", "No referer")
        user_id = request.session.get(self.user_identifier, "unknown guest")
        headers = dict(request.headers.items())

        if url.path != "/favicon.ico":
            logger.info(
                f"Method: {method}, URL: {url}, Client: {client}, Referer: {referer}, User ID: {user_id}, Headers: {headers}, Status Code: {status_code}, Process Time: {process_time}"
            )

        return response
