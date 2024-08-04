# -*- coding: utf-8 -*-
"""
This module, `pages.py`, is part of a web application that serves various web pages and API endpoints. It uses FastAPI to define routes for serving HTML content and handling API requests. The module includes functionality for redirecting to the OpenAPI documentation, serving an index page, and potentially more pages as defined further in the module. It leverages external libraries such as `httpx` for asynchronous HTTP requests and `loguru` for logging. Database interactions are handled through SQLAlchemy, with specific operations defined in the `db_ops` module.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating API routes and handling HTTP requests.
    - httpx: For making asynchronous HTTP requests.
    - loguru: For logging.
    - sqlalchemy: For database interactions.
    - db_tables: Contains the SQLAlchemy table definitions used in the application.
    - functions: Includes utility functions such as `update_timezone_for_dates` and `get_public_debt`.
    - resources: Provides access to common resources like `db_ops` for database operations and `templates` for rendering HTML content.
    - settings: Contains application settings.

Routes:
    - GET "/": Redirects to the OpenAPI documentation.
    - GET "/index": Serves the index page of the web application.
    - GET "/about": Serves the about page of the web application.

Usage:
    This module is designed to be integrated into a FastAPI application, providing a router for serving web pages and related API endpoints. It can be mounted on the main application to handle requests to the root and index endpoints, among others defined within the module.
"""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from httpx import AsyncClient
from loguru import logger
from sqlalchemy import Select

from ..db_tables import WebLinks, Posts
from ..functions.date_functions import update_timezone_for_dates
from ..functions.interesting_api_calls import get_public_debt
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()
client = AsyncClient()


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
    try:
        cool_stuff = await db_ops.read_query(
            Select(WebLinks)
            .limit(8)
            .order_by(WebLinks.date_created.desc())
        )
        cool_stuff = [thing.to_dict() for thing in cool_stuff]
        cool_stuff = await update_timezone_for_dates(
            data=cool_stuff, user_timezone=settings.default_timezone
        )
    except Exception as e:
        error: str = f"Error getting Interesting things: {e}"
        logger.error(error)
        cool_stuff = []

    try:
        posts = await db_ops.read_query(
            Select(Posts).limit(5).order_by(Posts.date_created.desc())
        )
        posts = [post.to_dict() for post in posts]
        posts = await update_timezone_for_dates(
            data=posts, user_timezone=settings.default_timezone
        )
    except Exception as e:
        error: str = f"Error getting Posts: {e}"
        logger.error(error)
        posts = []

    context = {
        "page": "pages",
        "data": {"my_stuff": {}, "cool_stuff": cool_stuff},
        "posts": posts,
    }
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
    context = {"page": "pages", "data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(request=request, name=template, context=context)


# # login to site
# @router.get("/login")
# async def login(request: Request):
#     context = {}
#     return templates.TemplateResponse(
#         request=request, name="users/login.html", context=context
#     )


@router.get("/data")
async def get_data_page(request: Request):
    context = {
        "page": "pages",
    }
    return templates.TemplateResponse(
        request=request, name="interesting-data.html", context=context
    )


@router.get("/public-debt")
async def public_debt(request: Request):
    debt_list = await get_public_debt()

    last_year = None
    for d in debt_list:
        year_hold = d["tot_pub_debt_out_amt"]

        # if d["debt_held_public_amt"] != 'null':
        #     d["debt_held_public_amt"] = "{:,.2f}".format(float(d["debt_held_public_amt"]))

        # if d["intragov_hold_amt"] != 'null':
        #     d["intragov_hold_amt"] = "{:,.2f}".format(float(d["intragov_hold_amt"]))

        # d["tot_pub_debt_out_amt"] = "{:,.2f}".format(float(d["tot_pub_debt_out_amt"]))

        if last_year is not None:
            d["debt_growth"] = round(
                ((float(year_hold) - float(last_year)) / float(year_hold)) * 100, 3
            )
            last_year = year_hold
        else:
            last_year = year_hold
            d["debt_growth"] = 0

    context = {"page": "pages", "debt": debt_list}

    return templates.TemplateResponse(
        request=request, name="api/us-debt.html", context=context
    )
