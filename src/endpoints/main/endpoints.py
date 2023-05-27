# -*- coding: utf-8 -*-
from loguru import logger
from starlette.responses import RedirectResponse

from endpoints.main import crud as lib_crud
from endpoints.main.functions import call_github_repos
from endpoints.main.functions import call_github_user
from resources import cool_stuff
# from resources import my_stuff
from resources import templates


async def homepage(request):
    return RedirectResponse(url="/index", status_code=303)


async def about_page(request):
    data_repo = await call_github_repos()
    data_user = await call_github_user()
    data: dict = {"data_repo": data_repo, "data_user": data_user}
    template: str = "about.html"
    context = {"request": request, "data": data}
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))
    return templates.TemplateResponse(template, context)


async def index(request):

    my_stuff = await call_github_repos()
    data: dict = {"my_stuff": my_stuff, "cool_stuff": cool_stuff}

    template: str = "index2.html"
    context = {"request": request, "data": data}
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))
    return templates.TemplateResponse(template, context)


async def login(request):
    template: str = "users/login.html"
    context = {"request": request, "data": None}
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))
    return templates.TemplateResponse(template, context)
