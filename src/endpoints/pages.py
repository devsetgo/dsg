# -*- coding: utf-8 -*-


import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from loguru import logger
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator
from sqlalchemy import Delete, Insert, Select, Update

from ..db_tables import InterestingThings, User
from ..functions.hash_function import check_needs_rehash, hash_password, verify_password
from ..resources import db_ops, statics, templates
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
    context = {"request": request, "data": {"my_stuff": {}, "cool_stuff": cool_stuff}}
    return templates.TemplateResponse("index2.html", context=context)


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
    context = {"request": request, "data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(template, context)


# login to site
@router.get("/login")
async def login(request: Request):
    context = {
        "request": request,
    }
    return templates.TemplateResponse("users/login.html", context=context)
