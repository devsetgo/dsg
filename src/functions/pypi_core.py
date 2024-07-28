# -*- coding: utf-8 -*-
"""
This module provides functions to fetch package data from PyPI and handle database operations.

Author:
    Mike Ryan
    MIT Licensed

Functions:
    fetch_package_data(client, package)
        Fetches package data from PyPI and returns a dictionary with package details.

Imports:
    re
        Provides regular expression matching operations.
    httpx
        Provides an HTTP client for making requests.
    loguru.logger
        Provides logging capabilities.
    sqlalchemy.Select
        Provides SQL select operations.
    tqdm.asyncio.async_tqdm
        Provides progress bar for asyncio tasks.
    ..db_tables
        Provides database table definitions.
    ..resources.db_ops
        Provides database operations.
"""
import csv
import random
import re
import uuid
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger
from sqlalchemy import Select
from tqdm.asyncio import tqdm as async_tqdm

from ..db_tables import Library, LibraryName, Requirement
from ..resources import db_ops


async def fetch_package_data(
    client: httpx.AsyncClient, package: Dict[str, Any]
) -> Dict[str, Any]:
    """Fetches package data from PyPI and returns a dictionary with package details.

    Args:
        client (httpx.AsyncClient): The HTTP client to use for making requests.
        package (Dict[str, Any]): A dictionary containing package information.

    Returns:
        Dict[str, Any]: A dictionary containing package details such as name, version, URL, description, vulnerabilities, etc.

    Raises:
        httpx.HTTPStatusError: If the request to PyPI fails.

    Example:
        package_data = await fetch_package_data(client, {"package_name": "requests"})
    """
    package_name = package.get("package_name", "unknown_package")
    url = f"https://pypi.org/pypi/{package_name}/json"
    logger.info(f"Fetching data from {url}")
    response = await client.get(url)
    if response.status_code == 200:
        data = response.json()
        info = data["info"]
        vulnerabilities = data.get("vulnerabilities", [])
        package_data = {
            "package_name": info.get("name", "unknown_name"),
            "current_version": package.get("current_version", "unknown_version"),
            "latest_version": info.get("version", "unknown_version"),
            "package_url": info.get("package_url", "unknown_url"),
            "package_description": info.get("summary", "No description available"),
            "vulnerabilities": vulnerabilities,
            "home_page": info.get("home_page", "unknown_home_page"),
            "author": info.get("author", "unknown_author"),
            "author_email": info.get("author_email", "unknown_author_email"),
            "license": info.get("license", "unknown_license"),
            "has_bracket": package.get("has_bracket", False),
            "bracket_content": package.get("bracket_content", ""),
        }
        logger.debug(f"Fetched data for package {package_data}")
        return package_data
    else:
        logger.error(f"Failed to fetch data for package {package_name}")
        return None


async def add_demo_data(qty: Optional[int] = 20) -> None:
    """Adds demo data to the database.

    This function reads a list of libraries from a CSV file and generates demo data.
    It creates a specified quantity of demo entries with random data and adds them to the database.

    Args:
        qty (Optional[int]): The number of demo entries to add. Defaults to 20.

    Returns:
        None

    Imports:
        csv: Provides functionality to read from and write to CSV files.
        random: Provides functions to generate random numbers.
        uuid: Provides functions to generate universally unique identifiers (UUIDs).

    Raises:
        FileNotFoundError: If the CSV file is not found.
        Exception: If there is an error during the database operation.

    Example:
        await add_demo_data(qty=50)
    """
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


async def check_packages(
    packages: List[str], request_group_id: str, request: Optional[object]
) -> None:
    """Checks the given list of packages by fetching their data from PyPI.

    This function cleans the provided list of packages and then fetches their data from PyPI.
    It uses an asynchronous HTTP client to perform the requests and processes the results.

    Args:
        packages (List[str]): A list of package names as strings.
        request_group_id (str): A unique identifier for the request group.
        request (Optional[object]): An optional request object (can be None).

    Returns:
        None

    Imports:
        httpx: Provides an HTTP client for making requests.
        loguru.logger: Provides logging capabilities.
        tqdm.asyncio.async_tqdm: Provides progress bar for asyncio tasks.

    Example:
        await check_packages(packages=["requests"], request_group_id="12345", request=None)
    """
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


def clean_packages(packages: List[str]) -> List[str]:
    """Cleans the given list of packages by removing invalid entries.

    This function processes a list of package names, ensuring that each entry is a valid string.
    It removes any lines that are comments, recursion references, or empty.

    Args:
        packages (List[str]): A list of package names as strings.

    Returns:
        List[str]: A cleaned list of package names.

    Raises:
        TypeError: If the input is not a list of strings.

    Example:
        cleaned = clean_packages(["requests", "# comment", "-r requirements.txt", ""])
        # cleaned will be ["requests"]
    """
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


async def store_package_data(
    package_data: Dict[str, str], request_group_id: str
) -> None:
    """Stores package data in the database.

    This function checks if the given package name already exists in the database.
    If it does not exist, it creates a new record for the package name.

    Args:
        package_data (Dict[str, str]): A dictionary containing package data with keys such as "package_name".
        request_group_id (str): A unique identifier for the request group.

    Returns:
        None

    Imports:
        db_ops: Provides database operations.
        loguru.logger: Provides logging capabilities.
        sqlalchemy.sql.Select: Provides SQL select statement construction.
        LibraryName: Represents the library name model in the database.

    Raises:
        Exception: If there is an error during the database operation.

    Example:
        await store_package_data(package_data={"package_name": "requests"}, request_group_id="12345")
    """
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
