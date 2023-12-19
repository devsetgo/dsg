# -*- coding: utf-8 -*-


from datetime import datetime
from typing import List
from loguru import logger
from fastapi import APIRouter, HTTPException, Query, status, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator
from sqlalchemy import Delete, Insert, Select, Update
import re
from ..functions.hash_function import hash_password, verify_password, check_needs_rehash

from ..resources import db_ops, templates, statics
from ..db_tables import User, InterestingThings


router = APIRouter()

# create index page route
@router.get("/",response_class=RedirectResponse)
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

    # cool_stuff = await db_ops.read_query(Select(InterestingThings))
    context = {"request": request,"data":{"my_stuff": {}, "cool_stuff": cool_stuff}}
    return templates.TemplateResponse("index2.html", context=context)

