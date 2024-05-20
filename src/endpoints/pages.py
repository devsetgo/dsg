# -*- coding: utf-8 -*-


from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import Select

from ..db_tables import InterestingThings
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


# create index page route
@router.get("/", response_class=RedirectResponse)
async def root():
    """
    Root endpoint of API
    Returns:
        Redrects to openapi document
    """
    # redirect to openapi docs
    logger.info("Redirecting to OpenAPI docs")
    return RedirectResponse(url="/pages/index")


@router.get("/index")
async def index(request: Request):
    cool_stuff = await db_ops.read_query(Select(InterestingThings))
    cool_stuff = [thing.to_dict() for thing in cool_stuff]
    context = {"data": {"my_stuff": {}, "cool_stuff": cool_stuff}}

    return templates.TemplateResponse(
        request=request, name="index2.html", context=context
    )


@router.get("/about")
async def about_page(request: Request):
    """
    This function handles requests to the /about URL. It calls the `call_github_repos` and `call_github_user`
    functions to retrieve data from GitHub, and then returns a template response containing that data.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    """

    from ..functions.github import call_github_repos, call_github_user

    # Retrieve data from GitHub using the `call_github_repos` and `call_github_user` functions.
    data_repo = await call_github_repos()
    data_user = await call_github_user()

    # Combine the retrieved data into a single dictionary.
    data: dict = {
        "data_repo": data_repo,
        "data_user": data_user,
        "repo_name": settings.github_id,
    }

    # Define the name of the HTML template to use for this page.
    template: str = "about.html"

    # Define the context variables to pass to the template.
    context = {"data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(request=request, name=template, context=context)


# login to site
@router.get("/login")
async def login(request: Request):
    context = {}
    return templates.TemplateResponse(
        request=request, name="users/login.html", context=context
    )
