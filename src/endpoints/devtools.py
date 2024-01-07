# -*- coding: utf-8 -*-

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, Body
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from loguru import logger
from pydantic import BaseModel, ConfigDict, EmailStr, Field, ValidationError, validator

from src.functions.pypi_core import check_packages  # , check_package

router = APIRouter()


@router.post("/pypi/check-list")
async def check_pypi_packages(packages: List[str] = Body(...)):
    logger.info(f"Checking packages: {packages}")
    try:
        data = await check_packages(packages)
        logger.info(f"Successfully checked packages: {packages}")
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Failed to check packages: {packages}. Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check packages")


@router.get("/pypi/check-one")
async def check_pypi_packages(package: str):
    logger.info(f"Checking package: {package}")
    try:
        packages = [package]
        data = await check_packages(packages)
        logger.info(f"Successfully checked package: {package}")
        return JSONResponse(data[0])
    except Exception as e:
        logger.error(f"Failed to check package: {package}. Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check package")
