# -*- coding: utf-8 -*-

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
    context = await get_pypi_metrics()
    return templates.TemplateResponse(
        request=request, name="/pypi/dashboard.html", context=context
    )


@router.get("/check")
async def get_check_form(request: Request):

    context = {
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
    pypi_response = await check_packages(
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
        "data": db_data_dict,
        "request_group_id": request_group_id,
    }

    response = templates.TemplateResponse(request, "pypi/result.html", context=context)
    return response


@router.get("/list")
async def get_all(request: Request):
    query = Select(Requirement)
    db_data = await db_ops.read_query(query=query, limit=100)
    count_data = await db_ops.count_query(query=query)

    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    context = {
        "db_data": db_data_dict,
        "count_data": count_data,
    }
    return templates.TemplateResponse(request, "pypi/simple-list.html", context=context)
