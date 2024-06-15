# -*- coding: utf-8 -*-

from typing import List
import uuid
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger
from src.functions.pypi_core import check_packages  # , check_package

router = APIRouter()


@router.post("/pypi/check-list")
async def post_check_pypi_packages(packages: List[str] = Body(...)):
    logger.info(f"Checking packages: {packages}")
    
    try:
        data = await check_packages(packages=packages,request_group_id=str(uuid.uuid4()),request=None)
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
        data = await check_packages(packages, request=None, request_group_id=str(uuid.uuid4()))
        logger.info(f"Successfully checked package: {package}")
        return JSONResponse(data[0])
    except Exception as e:

        logger.error(f"Failed to check package: {package}. Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check package")
