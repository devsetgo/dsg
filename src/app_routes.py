# -*- coding: utf-8 -*-
from dsg_lib.fastapi_functions import system_health_endpoints
# from fastapi import FastAPI, Request, HTTPException, status
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi_csrf_protect.exceptions import CsrfProtectError
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from .endpoints import admin, devtools, notes, pages, pypi, users
from .resources import templates


def create_routes(app: FastAPI):
    app.mount("/static", StaticFiles(directory="static"), name="static")

    ALL_HTTP_CODES = {
        400: {
            "description": "Bad Request",
            "extended_description": "The server could not understand the request due to invalid syntax.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/400",
        },
        401: {
            "description": "Unauthorized",
            "extended_description": "The request requires user authentication.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/401",
        },
        402: {
            "description": "Payment Required",
            "extended_description": "This code is reserved for future use.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/402",
        },
        403: {
            "description": "Forbidden",
            "extended_description": "The server understood the request, but it refuses to authorize it.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/403",
        },
        404: {
            "description": "Not Found",
            "extended_description": "The server can not find the requested resource.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/404",
        },
        405: {
            "description": "Method Not Allowed",
            "extended_description": "The method specified in the request is not allowed for the resource identified by the request URI.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/405",
        },
        406: {
            "description": "Not Acceptable",
            "extended_description": "The resource identified by the request is only capable of generating response entities which have content characteristics not acceptable according to the accept headers sent in the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/406",
        },
        407: {
            "description": "Proxy Authentication Required",
            "extended_description": "The client must first authenticate itself with the proxy.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/407",
        },
        408: {
            "description": "Request Timeout",
            "extended_description": "The server timed out waiting for the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/408",
        },
        409: {
            "description": "Conflict",
            "extended_description": "The request could not be completed due to a conflict with the current state of the resource.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/409",
        },
        410: {
            "description": "Gone",
            "extended_description": "The requested resource is no longer available at the server and no forwarding address is known.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/410",
        },
        411: {
            "description": "Length Required",
            "extended_description": "The server refuses to accept the request without a defined Content-Length.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/411",
        },
        412: {
            "description": "Precondition Failed",
            "extended_description": "The precondition given in one or more of the request-header fields evaluated to false when it was tested on the server.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/412",
        },
        413: {
            "description": "Payload Too Large",
            "extended_description": "The server is refusing to process a request because the request payload is larger than the server is willing or able to process.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/413",
        },
        414: {
            "description": "URI Too Long",
            "extended_description": "The server is refusing to service the request because the request-target is longer than the server is willing to interpret.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/414",
        },
        415: {
            "description": "Unsupported Media Type",
            "extended_description": "The media format of the requested data is not supported by the server, so the server is rejecting the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/415",
        },
        416: {
            "description": "Range Not Satisfiable",
            "extended_description": "The range specified in the Range header field of the request can't be fulfilled; it's possible that the range is outside the size of the target URI's data.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/416",
        },
        417: {
            "description": "Expectation Failed",
            "extended_description": "The expectation given in the Expect request header could not be met by the server.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/417",
        },
        418: {
            "description": "I'm a teapot",
            "extended_description": "The server refuses to brew coffee because it is, permanently, a teapot. A combined coffee/tea pot that is temporarily out of coffee should instead return 503. This error is a reference to Hyper Text Coffee Pot Control Protocol defined in April Fools' jokes in 1998 and 2014.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/418",
        },
        421: {
            "description": "Misdirected Request",
            "extended_description": "The request was directed at a server that is not able to produce a response. This can be sent by a server that is not configured to produce responses for the combination of scheme and authority that are included in the request URI.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/421",
        },
        422: {
            "description": "Unprocessable Entity",
            "extended_description": "The server understands the content type of the request entimy, and the syntax of the request entity is correct, but it was unable to process the contained instructions.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/422",
        },
        423: {
            "description": "Locked",
            "extended_description": "The resource that is being accessed is locked.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/423",
        },
        424: {
            "description": "Failed Dependency",
            "extended_description": "The request failed due to failure of a previous request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/424",
        },
        425: {
            "description": "Too Early",
            "extended_description": "Indicates that the server is unwilling to risk processing a request that might be replayed.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/425",
        },
        426: {
            "description": "Upgrade Required",
            "extended_description": "The server refuses to perform the request using the current protocol but might be willing to do so after the client upgrades to a different protocol. The server sends an Upgrade header in a 426 response to indicate the required protocol(s).",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/426",
        },
        428: {
            "description": "Precondition Required",
            "extended_description": "The origin server requires the request to be conditional. This response is intended to prevent the 'lost update' problem, where a client GETs a resource's state, modifies it, and PUTs it back to the server, when meanwhile a third party has modified the state on the server, leading to a conflict.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/428",
        },
        429: {
            "description": "Too Many Requests",
            "extended_description": "The user has sent too many requests in a given amount of time ('rate limiting').",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/429",
        },
        431: {
            "description": "Request Header Fields Too Large",
            "extended_description": "The server is unwilling to process the request because its header fields are too large.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/431",
        },
        451: {
            "description": "Unavailable For Legal Reasons",
            "extended_description": "The server is denying access to the resource as a consequence of a legal demand.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/451",
        },
        500: {
            "description": "Internal Server Error",
            "extended_description": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/500",
        },
        501: {
            "description": "Not Implemented",
            "extended_description": "The server does not support the functionality required to fulfill the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/501",
        },
        502: {
            "description": "Bad Gateway",
            "extended_description": "The server, while acting as a gateway or proxy, received an invalid response from an inbound server it accessed while attempting to fulfill the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/502",
        },
        503: {
            "description": "Service Unavailable",
            "extended_description": "The server is currently unable to handle the request due to a temporary overload or scheduled maintenance, which will likely be alleviated after some delay.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503",
        },
        504: {
            "description": "Gateway Timeout",
            "extended_description": "The server, while acting as a gateway or proxy, did not receive a timely response from an upstream server it needed to access in order to complete the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/504",
        },
        505: {
            "description": "HTTP Version Not Supported",
            "extended_description": "The server does not support, or refuses to support, the major version of HTTP that was used in the request message.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/505",
        },
        506: {
            "description": "Variant Also Negotiates",
            "extended_description": "The server has an internal configuration error: the chosen variant resource is configured to engage in transparent content negotiation itself, and is therefore not a proper end point in the negotiation process.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/506",
        },
        507: {
            "description": "Insufficient Storage",
            "extended_description": "The method could not be performed on the resource because the server is unable to store the representation needed to successfully complete the request.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/507",
        },
        508: {
            "description": "Loop Detected",
            "extended_description": "The server detected an infinite loop while processing a request with 'Depth: infinity'. This status indicates that the entire operation failed.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/508",
        },
        510: {
            "description": "Not Extended",
            "extended_description": "Further extensions to the request are required for the server to fulfill it.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/510",
        },
        511: {
            "description": "Network Authentication Required",
            "extended_description": "The client needs to authenticate to gain network access. Intended for use by intercepting proxies used to control access to the network.",
            "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/511",
        },
    }

    @app.exception_handler(CsrfProtectError)
    def csrf_protect_exception_handler(_: Request, exc: CsrfProtectError):
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.message}
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        error_code = exc.status_code
        if error_code not in ALL_HTTP_CODES:
            error_code = 500  # default to Internal Server Error
        logger.error(f"{error_code} error: {exc}")
        return RedirectResponse(url=f"/error/{error_code}")

    # @app.exception_handler(status.HTTP_404_NOT_FOUND)
    # async def not_found_exception_handler(request: Request, exc: HTTPException):
    #     logger.error(f"404 error: {exc}")
    #     return RedirectResponse(url=f"/error/{exc.status_code}")

    app.include_router(
        admin.router,
        prefix="/admin",
        tags=["admin"],
    )

    app.include_router(
        devtools.router,
        prefix="/devtools",
        tags=["devtools"],
    )

    @app.get("/error/{error_code}")
    async def error_page(request: Request, error_code: int):
        context = {
            "request": request,
            "error_code": error_code,
            "description": ALL_HTTP_CODES[error_code]["description"],
            "extended_description": ALL_HTTP_CODES[error_code]["extended_description"],
            "link": ALL_HTTP_CODES[error_code]["link"],
        }
        return templates.TemplateResponse("error/error-page.html", context)

    app.include_router(
        notes.router,
        prefix="/notes",
        tags=["notes"],
    )
    app.include_router(
        pages.router,
        prefix="/pages",
        tags=["html-pages"],
    )

    app.include_router(
        pypi.router,
        prefix="/pypi",
        tags=["pypi"],
    )
    app.include_router(
        users.router,
        prefix="/users",
        tags=["users"],
    )

    # This should always be the last route added to keep it at the bottom of the OpenAPI docs
    config_health = {
        "enable_status_endpoint": True,
        "enable_uptime_endpoint": True,
        "enable_heapdump_endpoint": True,
    }

    app.include_router(
        system_health_endpoints.create_health_router(config=config_health),
        prefix="/api/health",
        tags=["system-health"],
    )
