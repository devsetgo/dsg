# -*- coding: utf-8 -*-
import random
import uuid
from datetime import datetime
from datetime import timedelta

from loguru import logger

from com_lib import crud_ops
from com_lib.db_setup import libraries
from com_lib.db_setup import requirements


def get_date():
    return datetime.now()


async def store_in_data(store_values: dict):

    query = requirements.insert()
    await crud_ops.execute_one_db(query=query, values=store_values)
    rgi = store_values["request_group_id"]
    logger.info(f"Created {rgi}")
    # return request_group_id


async def store_lib_request(json_data: dict, request_group_id: str):

    now = get_date()
    query = libraries.insert()
    values = {
        "id": str(uuid.uuid4()),
        "request_group_id": request_group_id,
        "library": json_data["library"],
        "currentVersion": json_data["currentVersion"],
        "newVersion": json_data["newVersion"],
        "dated_created": now,
    }
    await crud_ops.execute_one_db(query=query, values=values)
    logger.info(f"created request_group_id: {request_group_id}")


async def store_lib_data(request_group_id: str, json_data: dict):

    bulk_data: list = []
    for j in json_data:
        lib_update: dict = {
            "id": str(uuid.uuid4()),
            "request_group_id": request_group_id,
            "library": j["library"],
            "currentVersion": j["currentVersion"],
            "newVersion": j["newVersion"],
            "dated_created": datetime.now(),
        }
        bulk_data.append(lib_update)

    query = libraries.insert()
    values = bulk_data
    await crud_ops.execute_many_db(query=query, values=values)
    logger.info(f"created request_group_id: {request_group_id}")
    return request_group_id


async def get_request_group_id(request_group_id: str):

    query = requirements.select().where(
        requirements.c.request_group_id == request_group_id
    )
    result = await crud_ops.fetch_one_db(query=query)
    logger.debug(str(result))
    logger.info(f"returning results for {request_group_id}")
    return result


import collections

from loguru import logger

from com_lib import crud_ops
from com_lib.db_setup import libraries
from com_lib.db_setup import requirements


async def get_data():

    query = libraries.select()
    data = await crud_ops.fetch_all_db(query=query)

    lib_data_month = await process_by_month(data)
    lib_sum = await sum_lib(lib_data_month)
    library_data_count = await process_by_lib(data)
    lib_data_sum = await sum_lib_count(library_data_count)
    lib_new_ver = await lib_new_versions(data)

    result = {
        "lib_data_month": lib_data_month,
        "lib_sum": lib_sum,
        "library_data_count": library_data_count,
        "lib_data_sum": lib_data_sum,
        "lib_new_ver": lib_new_ver,
    }
    return result


async def lib_new_versions(data: dict):

    ver = []
    for d in data:

        lib_ver = f'{d["library"]}={d["newVersion"]}'
        if lib_ver not in ver:
            ver.append(lib_ver)
    result = len(ver)

    return result


async def process_by_month(data: dict) -> dict:
    """
    Count by month of libraries checked
    """
    result: dict = {}
    for d in data:
        date_item = d["dated_created"]
        ym = date_item.strftime("%Y-%m")
        if ym not in result:
            result[ym] = 1
        else:
            result[ym] += 1

    logger.debug(result)
    return result


async def sum_lib(data: dict):

    result: int = sum(data.values())
    logger.debug(result)
    return result


async def process_by_lib(data: dict) -> dict:
    """
    Count by number of versions of library & how often checked
    """
    library_list = []
    for d in data:
        library_list.append(d["library"])
    result: dict = dict(collections.Counter(library_list).most_common(25))
    logger.debug(f"by library: {result}")
    return result


async def sum_lib_count(data: dict):

    result: int = sum(data.values())
    logger.debug(result)
    return result


async def requests_data():

    query = requirements.select()
    data = await crud_ops.fetch_all_db(query=query)

    ips = []
    for d in data:
        if d["host_ip"] not in ips:
            ips.append(d["host_ip"])

    result = {"unique": len(ips), "fulfulled": len(data)}
    logger.debug(result)
    return result
