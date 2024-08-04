# -*- coding: utf-8 -*-
"""
This module provides developer tools for interacting with PyPI (Python Package Index), specifically for checking package information. It includes endpoints to check a list of packages or a single package against PyPI to retrieve their details or status. The functionality is exposed via FastAPI routes, making it suitable for integration into web applications that require information on Python packages.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating API routes.
    - loguru: For logging.
    - uuid: For generating unique request identifiers.
    - src.functions.pypi_core: Contains the core functionality for interacting with PyPI.

Routes:
    - POST /pypi/check-list: Accepts a list of package names and returns their details from PyPI.
    - GET /pypi/check-one: Accepts a single package name as a query parameter and returns its details from PyPI.

Usage:
    This module is intended to be used as part of a larger application that requires information about Python packages from PyPI. It can be mounted on a FastAPI application to provide API endpoints for checking package details.
"""
import uuid
from typing import List

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from src.functions.pypi_core import check_packages  # , check_package

router = APIRouter()


@router.post("/pypi/check-list")
async def post_check_pypi_packages(packages: List[str] = Body(...)):
    logger.info(f"Checking packages: {packages}")

    try:
        data = await check_packages(
            packages=packages, request_group_id=str(uuid.uuid4()), request=None
        )
        logger.info(f"Successfully checked packages: {packages}")
        return JSONResponse(data)
    except Exception as e:
        print(e)
        logger.error(f"Failed to check packages: {packages}. Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check packages")


@router.get("/pypi/check-one")
async def get_check_pypi_packages(package: str):
    logger.info(f"Checking package: {package}")
    print(package)
    try:
        packages = [package]
        data = await check_packages(
            packages, request=None, request_group_id=str(uuid.uuid4())
        )
        logger.info(f"Successfully checked package: {package}")
        return JSONResponse(data[0])
    except Exception as e:
        logger.error(f"Failed to check package: {package}. Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check package")
