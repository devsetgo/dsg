# -*- coding: utf-8 -*-
from loguru import logger
from starlette.responses import RedirectResponse

from endpoints.main import crud as lib_crud
from resources import templates


async def homepage(request):
    return RedirectResponse(url="/index", status_code=303)


async def about_page(request):

    template: str = "about.html"
    context: dict = {"request": request}
    logger.info(f"page accessed: /{template}")
    return templates.TemplateResponse(template, context)


async def index(request):

    from endpoints.main.functions import call_github
    data = await call_github()
    template: str = "index2.html"
    context = {"request": request, "data": data}
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))
    return templates.TemplateResponse(template, context)
