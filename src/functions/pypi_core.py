# -*- coding: utf-8 -*-
"""

Author:
    Mike Ryan
    MIT Licensed
"""
import re

import httpx
from loguru import logger
from sqlalchemy import Select
from tqdm.asyncio import tqdm as async_tqdm

from ..db_tables import Library, LibraryName, Requirement
from ..resources import db_ops


async def fetch_package_data(client, package):
    url = f"https://pypi.org/pypi/{package['package_name']}/json"
    logger.info(f"Fetching data from {url}")
    response = await client.get(url)
    if response.status_code == 200:
        data = response.json()
        info = data["info"]
        vulnerabilities = data["vulnerabilities"]
        package_data = {
            "package_name": info["name"],
            "current_version": package["current_version"],
            "latest_version": info["version"],
            "package_url": info["package_url"],
            "package_description": info["summary"],
            "vulnerabilities": vulnerabilities,
            "home_page": info["home_page"],
            "author": info["author"],
            "author_email": info["author_email"],
            "license": info["license"],
            "has_bracket": package["has_bracket"],
            "bracket_content": package["bracket_content"],
        }
        logger.debug(f"Fetched data for package {package_data}")
        return package_data
    else:
        logger.error(f"Failed to fetch data for package {package['package_name']}")


async def add_demo_data(qty=20):
    import csv
    import random
    import uuid

    # list of libraries from file
    file = open("data/csv/__pypi_demo.csv", "r")
    with file as f:
        reader = csv.reader(f)
        data = list(reader)
        # print(data)

    data_list: list = []
    for d in data:
        # print(d)
        data_list.append(d[0])
    # print(data_list)

    async for _i in async_tqdm(range(qty), desc="Adding demo PYPI data", leave=False):
        # get 2-10 packages from data using random
        sample_size = min(
            len(data_list), random.randint(2, 20)
        )  # get a random integer between 2 and 20, but not more than the length of the list
        packages = random.sample(data_list, sample_size)
        # call check_packages
        await check_packages(
            packages=packages, request_group_id=str(uuid.uuid4()), request=None
        )


async def check_packages(packages: list, request_group_id: str, request):
    logger.debug(
        f"Starting check_packages with packages: {packages} and request_group_id:\
             {request_group_id}"
    )
    cleaned_packages = clean_packages(packages)
    async with httpx.AsyncClient(
        timeout=90.0
    ) as client:  # Increase timeout to 30 seconds
        tasks = [fetch_package_data(client, package) for package in cleaned_packages]
        results = []
        for f in async_tqdm.as_completed(
            tasks, total=len(tasks), desc="Fetching package data", leave=False
        ):
            result = await f
            results.append(result)

    # store package data in the database after all calls are complete
    for package_data in results:
        if package_data is not None:
            await store_package_data(package_data, request_group_id)

    # Extract host and header data from the request
    if request is not None:
        host_ip = request.client.host
        header_data = dict(request.headers)
    else:
        host_ip = None
        header_data = None
    # Create a new Requirement record
    requirement = Requirement(
        request_group_id=request_group_id,
        text_in="\n".join(packages),
        json_data_in=cleaned_packages,
        json_data_out=results,
        lib_out_count=len(results),
        lib_in_count=len(packages),
        host_ip=host_ip,
        header_data=header_data,
    )

    # Store the Requirement record in the database
    await db_ops.create_one(requirement)

    logger.debug(
        f"Finished check_packages with packages: {packages} and request_group_id:\
             {request_group_id}"
    )
    return [result for result in results if result is not None]


def clean_packages(packages):
    logger.debug(f"Starting clean_packages with packages: {packages}")
    if not isinstance(packages, list) or not all(
        isinstance(package, str) for package in packages
    ):
        logger.error("Packages must be a list of strings")
        raise TypeError("Packages must be a list of strings")

    cleaned_packages = []
    for package in packages:
        # Skip lines with comments, recursion references, or empty lines
        if package.startswith("#") or package.startswith("-") or not package.strip():
            continue

        # Initialize values
        has_bracket = False
        bracket_content = None

        # Check if package contains []. If so, set has_bracket to True
        #  and get string inside [].
        if "[" in package:
            has_bracket = True
            bracket_content = re.search(r"\[(.*?)\]", package).group(1)

        # Replace signs before splitting
        new_package = re.sub(r"(==|>=|<=|>|<)", " ", package)

        # Remove unnecessary text
        cleaned_up_package = re.sub(r"[\(\[].*?[\)\]]", "", new_package)

        # Split library name from version and get values
        pipItem = cleaned_up_package.split()
        library = pipItem[0]
        currentVersion = pipItem[1] if len(pipItem) > 1 else "none"

        # Create dictionary with relevant information
        cleaned_lib = {
            "package_name": library,
            "current_version": currentVersion,
            "has_bracket": has_bracket,
            "bracket_content": bracket_content,
        }

        cleaned_packages.append(cleaned_lib)

    logger.debug(f"Finished clean_packages with cleaned_packages: {cleaned_packages}")
    return cleaned_packages


async def store_package_data(package_data: dict, request_group_id: str):
    logger.debug(
        f"Starting store_package_data with package_data: {package_data} and\
             request_group_id: {request_group_id}"
    )
    # Check if the library name already exists in the database
    library_name_results = await db_ops.read_query(
        Select(LibraryName).where(LibraryName.name == package_data["package_name"])
    )

    if len(library_name_results) == 0:
        # If the library name does not exist, create a new LibraryName record
        library_name = LibraryName(name=package_data["package_name"])
        await db_ops.create_one(library_name)
        library_name_results = await db_ops.read_query(
            Select(LibraryName).where(LibraryName.name == package_data["package_name"])
        )

    # Extract the LibraryName object from the list
    library_name = library_name_results[0]

    # Create a new Library record with the package data
    library = Library(
        request_group_id=request_group_id,
        library_id=library_name.pkid,
        current_version=package_data["current_version"],
        new_version=package_data["latest_version"],
        new_version_vulnerability=bool(
            package_data["vulnerabilities"]
        ),  # Set to True if vulnerabilities exist
        vulnerability=package_data["vulnerabilities"],
    )

    try:
        await db_ops.create_one(library)
        logger.debug(f"Successfully stored package data: {package_data}")
    except Exception as e:
        logger.error(f"Failed to store package data: {package_data}. Error: {e}")
    logger.debug(
        f"Finished store_package_data with package_data: {package_data} and\
             request_group_id: {request_group_id}"
    )
