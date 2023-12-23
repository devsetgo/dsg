# -*- coding: utf-8 -*-


import re
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator
from sqlalchemy import Delete, Insert, Select, Update

from ..db_tables import InterestingThings, User
from ..functions.hash_function import check_needs_rehash, hash_password, verify_password
from ..resources import db_ops, statics, templates

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
    }  # Use the generated CSRF token
    response = templates.TemplateResponse("pypi/new.html", context=context)
    csrf_protect.set_csrf_cookie(
        signed_token, response
    )  # Set the signed CSRF token in the cookie
    return response


@router.post("/check")
async def post_check_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    form = await request.form()
    print(form)
    # Validate the CSRF token
    await csrf_protect.validate_csrf(
        request
    )  # Pass the request object, not the csrf_token string
    # get form data from request

    data = [form]
    response = templates.TemplateResponse(
        "pypi/simple.html", {"request": request, "data": data}
    )
    csrf_protect.unset_csrf_cookie(response)  # prevent token reuse
    return response
