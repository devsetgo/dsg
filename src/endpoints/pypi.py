# -*- coding: utf-8 -*-

import uuid
import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError

from loguru import logger
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator
from sqlalchemy import Delete, Insert, Select, Update

from ..db_tables import InterestingThings, User, Library, LibraryName, Requirement
from ..functions.hash_function import check_needs_rehash, hash_password, verify_password
from ..resources import db_ops, statics, templates
from ..functions.pypi_core import check_packages

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
    context = {"request": request}
    return templates.TemplateResponse("dashboard.html", context=context)


@router.get("/check")
async def get_check_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()

    context = {
        "request": request,
        "csrf_token": csrf_token,
        "request_group_id": str(uuid.uuid4()),
    }  # Use the generated CSRF token
    response = templates.TemplateResponse("pypi/new.html", context=context)
    csrf_protect.set_csrf_cookie(
        signed_token, response
    )  # Set the signed CSRF token in the cookie
    return response


@router.post("/check", response_class=RedirectResponse)
async def post_check_form(
    request: Request, request_group_id: str, csrf_protect: CsrfProtect = Depends()
):
    form = await request.form()
    # Validate the CSRF token
    await csrf_protect.validate_csrf(
        request
    )  # Pass the request object, not the csrf_token string
    # get form data from request

    # convert this to a list
    data = form["requirements"]
    data = data.split("\n")
    data = [x.strip() for x in data]
    data = [x for x in data if x != ""]
    # check packages
    pypi_response = await check_packages(
        packages=data, request_group_id=request_group_id, request=request
    )

    # db_data = await db_ops.read_query(Select(Library).where(Library.request_group_id == request_group_id))
    # db_data_dict = [{k: v for k, v in item.__dict__.items() if not k.startswith('_')} for item in db_data]

    # response = templates.TemplateResponse(
    #     "pypi/simple.html", {"request": request, "data": data,"pypi_response":pypi_response,"db_data":db_data_dict,"request_group_id":request_group_id}
    # )
    # csrf_protect.unset_csrf_cookie(response)  # prevent token reuse
    # return response
    return RedirectResponse(url=f"/pypi/check/{request_group_id}", status_code=303)


@router.get("/check/{request_group_id}")
async def get_response(
    request: Request, request_group_id: str, csrf_protect: CsrfProtect = Depends()
):
    db_data = await db_ops.read_query(
        Select(Requirement).where(Requirement.request_group_id == request_group_id)
    )
    db_data_dict = [
        {k: v for k, v in item.__dict__.items() if not k.startswith("_")}
        for item in db_data
    ]

    response = templates.TemplateResponse(
        "pypi/result.html",
        {
            "request": request,
            "data": db_data_dict,
            "request_group_id": request_group_id,
        },
    )
    csrf_protect.unset_csrf_cookie(response)  # prevent token reuse
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

    response = templates.TemplateResponse(
        "pypi/simple-list.html",
        {
            "request": request,
            "db_data": db_data_dict,
            "count_data": count_data,
        },
    )

    return response


# from fastapi import FastAPI

# app = FastAPI()
# @app.exception_handler(CsrfProtectError)
# def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
#     return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
