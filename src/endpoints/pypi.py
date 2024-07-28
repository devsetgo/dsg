# -*- coding: utf-8 -*-
"""
This Python module, `pypi.py`, is designed to interact with the Python Package Index (PyPI) by providing a set of API endpoints for querying package information and metrics. It utilizes FastAPI for routing, SQLAlchemy for database interactions, and custom functions for direct PyPI queries. The module is part of a larger application aimed at providing tools and insights into Python packages.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating API routes and handling HTTP requests.
    - loguru: For logging.
    - sqlalchemy: For constructing and executing SQL queries.
    - uuid: For generating unique identifiers.
    - db_tables: Contains the SQLAlchemy table definitions, specifically for Python package requirements.
    - functions.pypi_core: Includes core functionalities for checking package details against PyPI.
    - functions.pypi_metrics: Provides functionalities for fetching metrics related to PyPI packages.
    - resources: Provides access to common resources like database operations (`db_ops`) and HTML templates.

API Endpoints:
    - GET "/": Redirects to the OpenAPI documentation for the API.
    - GET "/index": Serves the index page, potentially including metrics and insights into PyPI packages.
    - GET "/check": Displays a form for users to input package requirements for checking against PyPI.
    - POST "/check": Processes the form data submitted by users to check package requirements against PyPI.
    - GET "/check/{request_group_id}": Displays the results of the package requirements checked against PyPI.
    - GET "/list": Lists all package requirements stored in the database.

Usage:
    This module is intended to be used as part of a FastAPI application. It can be mounted as a router to handle specific paths, providing a subset of the application's overall functionality focused on PyPI package information and metrics.
"""
import uuid

from fastapi import APIRouter, Request, Response
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import Select

from ..db_tables import Requirement
from ..functions.pypi_core import check_packages
from ..functions.pypi_metrics import get_pypi_metrics
from ..resources import db_ops, templates

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
    return RedirectResponse(url="/pypi/index")


@router.get("/index")
async def index(request: Request):
    context = {"page": "tools"}
    metrics = await get_pypi_metrics()

    for k, v in metrics.items():
        context[k] = v

    from dsg_lib.common_functions.file_functions import save_text

    save_text(data=str(metrics), file_name="pypi_metrics.txt")

    return templates.TemplateResponse(
        request=request, name="/pypi/dashboard.html", context=context
    )


@router.get("/check")
async def get_check_form(request: Request):
    context = {
        "page": "tools",
        "request_group_id": str(uuid.uuid4()),
    }
    logger.info("Creating template response.")
    response = templates.TemplateResponse(
        request=request, name="pypi/new.html", context=context
    )

    logger.info("Returning response.")
    return response


@router.post("/check", response_class=RedirectResponse)
async def post_check_form(
    request: Request,
    request_group_id: str,
):
    form = await request.form()

    # convert this to a list
    data = form["requirements"]
    data = data.split("\n")
    data = [x.strip() for x in data]
    data = [x for x in data if x != ""]
    # check packages
    await check_packages(
        packages=data, request_group_id=request_group_id, request=request
    )

    return Response(
        headers={"HX-Redirect": f"/pypi/check/{request_group_id}"}, status_code=303
    )


@router.get("/check/{request_group_id}")
async def get_response(
    request: Request,
    request_group_id: str,
):
    db_data = await db_ops.read_query(
        Select(Requirement).where(Requirement.request_group_id == request_group_id)
    )
    if len(db_data) == 0:
        return RedirectResponse(url="/error/404", status_code=303)
    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    context = {
        "page": "tools",
        "data": db_data_dict,
        "request_group_id": request_group_id,
    }

    response = templates.TemplateResponse(request, "pypi/result.html", context=context)
    return response


@router.get("/list")
async def get_all(request: Request, limit=1000):
    query = Select(Requirement).limit(limit)
    db_data = await db_ops.read_query(query=query)
    count_data = await db_ops.count_query(query=query)

    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    context = {
        "page": "tools",
        "db_data": db_data_dict,
        "count_data": count_data,
    }
    return templates.TemplateResponse(request, "pypi/simple-list.html", context=context)
