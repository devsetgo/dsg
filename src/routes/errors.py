# -*- coding: utf-8 -*-
"""Error pages, described with dsg_lib's HTTP code table."""

from dsg_lib.web_common import http_codes
from robyn import Response

from ..templating import render

_CODES = http_codes.generate_code_dict([400, 404, 405, 422, 500])


def error_page(status_code: int, description: str | None = None) -> Response:
    info = _CODES.get(status_code, {"description": "Error", "extended_description": ""})
    return render(
        "error/error-page.html",
        status_code=status_code,
        code=status_code,
        title=info["description"],
        description=description or info["extended_description"],
    )
