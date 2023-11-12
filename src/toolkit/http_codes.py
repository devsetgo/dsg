# -*- coding: utf-8 -*-
# Python code to define a dictionary of HTTP error codes and their respective descriptions.
"""
Dictionary of HTTP error codes and their descriptions based on the HTTP/1.1 specification.
The dictionary provides a mapping between HTTP error codes and their description strings.
Use example:
- `http_codes` can be used to define or handle custom error responses for an API,
- GET_CODES, POST_CODES, PUT_CODES, PATCH_CODES, and DELETE_CODES can be used to define HTTP error codes commonly encountered with each type of request method in an API.
"""

http_codes = {
    100: {"description": "Continue"},
    101: {"description": "Switching Protocols"},
    102: {"description": "Processing"},
    103: {"description": "Early Hints"},
    200: {"description": "OK"},
    201: {"description": "Created"},
    202: {"description": "Accepted"},
    203: {"description": "Non-Authoritative Information"},
    204: {"description": "No Content"},
    205: {"description": "Reset Content"},
    206: {"description": "Partial Content"},
    207: {"description": "Multi-Status"},
    208: {"description": "Already Reported"},
    226: {"description": "IM Used"},
    300: {"description": "Multiple Choices"},
    301: {"description": "Moved Permanently"},
    302: {"description": "Found"},
    303: {"description": "See Other"},
    304: {"description": "Not Modified"},
    305: {"description": "Use Proxy"},
    306: {"description": "(Unused)"},
    307: {"description": "Temporary Redirect"},
    308: {"description": "Permanent Redirect"},
    400: {"description": "Bad Request"},
    401: {"description": "Unauthorized"},
    402: {"description": "Payment Required"},
    403: {"description": "Forbidden"},
    404: {"description": "Not Found"},
    405: {"description": "Method Not Allowed"},
    406: {"description": "Not Acceptable"},
    407: {"description": "Proxy Authentication Required"},
    408: {"description": "Request Timeout"},
    409: {"description": "Conflict"},
    410: {"description": "Gone"},
    411: {"description": "Length Required"},
    412: {"description": "Precondition Failed"},
    413: {"description": "Payload Too Large"},
    414: {"description": "URI Too Long"},
    415: {"description": "Unsupported Media Type"},
    416: {"description": "Range Not Satisfiable"},
    417: {"description": "Expectation Failed"},
    418: {"description": "I'm a teapot"},
    421: {"description": "Misdirected Request"},
    422: {"description": "Unprocessable Entity"},
    423: {"description": "Locked"},
    424: {"description": "Failed Dependency"},
    425: {"description": "Too Early"},
    426: {"description": "Upgrade Required"},
    428: {"description": "Precondition Required"},
    429: {"description": "Too Many Requests"},
    431: {"description": "Request Header Fields Too Large"},
    451: {"description": "Unavailable For Legal Reasons"},
    500: {"description": "Internal Server Error"},
    501: {"description": "Not Implemented"},
    502: {"description": "Bad Gateway"},
    503: {"description": "Service Unavailable"},
    504: {"description": "Gateway Timeout"},
    505: {"description": "HTTP Version Not Supported"},
    506: {"description": "Variant Also Negotiates"},
    507: {"description": "Insufficient Storage"},
    508: {"description": "Loop Detected"},
    510: {"description": "Not Extended"},
    511: {"description": "Network Authentication Required"},
}

# Define dictionaries for each HTTP method that map commonly encountered HTTP error codes to their descriptions.
# Each key-value pair maps an HTTP error code to its corresponding description in the http_codes dictionary.

# GET common error codes
GET_CODES = {
    200: http_codes[200],
    307: http_codes[307],
    400: http_codes[400],
    401: http_codes[401],
    403: http_codes[403],
    404: http_codes[404],
    408: http_codes[408],
    418: http_codes[418],
    429: http_codes[429],
    500: http_codes[500],
    503: http_codes[503],
}

# POST common error codes
POST_CODES = {
    201: http_codes[201],
    307: http_codes[307],
    400: http_codes[400],
    401: http_codes[401],
    403: http_codes[403],
    404: http_codes[404],
    408: http_codes[408],
    413: http_codes[413],
    418: http_codes[418],
    429: http_codes[429],
    500: http_codes[500],
    503: http_codes[503],
}

# PUT common error codes
PUT_CODES = {
    200: http_codes[200],
    204: http_codes[204],
    400: http_codes[400],
    401: http_codes[401],
    403: http_codes[403],
    404: http_codes[404],
    408: http_codes[408],
    413: http_codes[413],
    418: http_codes[418],
    429: http_codes[429],
    500: http_codes[500],
    503: http_codes[503],
}

# PATCH common error codes
PATCH_CODES = {
    200: http_codes[200],
    204: http_codes[204],
    400: http_codes[400],
    401: http_codes[401],
    403: http_codes[403],
    404: http_codes[404],
    408: http_codes[408],
    413: http_codes[413],
    418: http_codes[418],
    429: http_codes[429],
    500: http_codes[500],
    503: http_codes[503],
}

# DELETE common error codes
DELETE_CODES = {
    200: http_codes[200],
    204: http_codes[204],
    400: http_codes[400],
    401: http_codes[401],
    403: http_codes[403],
    404: http_codes[404],
    408: http_codes[408],
    418: http_codes[418],
    429: http_codes[429],
    500: http_codes[500],
    503: http_codes[503],
}

SYSTEM_INFO_CODE = {
    200: http_codes[200],
    409: http_codes[409],
    500: http_codes[500],
}
