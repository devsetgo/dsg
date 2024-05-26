# -*- coding: utf-8 -*-
"""
pypi_core.py

This module contains functions for fetching and storing package data from PyPI (Python Package Index).

It includes the following functions:
- fetch_package_data: Fetches package data from PyPI for a specific package.
- check_packages: Checks a list of packages for updates and vulnerabilities.
- store_package_data: Stores package data in the database.

The package data includes the package name, current version, latest version, package URL, package description,
vulnerabilities, home page, author, author email, license, and bracket-related info.

This module uses the httpx library for sending HTTP requests, the loguru library for logging, and the sqlalchemy library
for interacting with the database. It also uses the tqdm library for displaying progress bars when fetching package data.
"""
import re
from typing import Dict, List, Union

import httpx
from loguru import logger
from sqlalchemy import Select

from ..db_tables import Library, LibraryName
from ..resources import db_ops


async def fetch_package_data(client: httpx.Client, package: Dict[str, Union[str, bool]]) -> Dict[str, Union[str, bool, List[Dict[str, str]]]]:
    """
    Fetches package data from PyPI.

    This function sends a GET request to the PyPI API for a specific package and extracts relevant information
    from the response. The extracted information includes the package name, current version, latest version,
    package URL, package description, vulnerabilities, home page, author, author email, license, and bracket-related info.

    Args:
        client (httpx.Client): The HTTP client used to send the request.
        package (Dict[str, Union[str, bool]]): A dictionary containing the package name and current version.

    Returns:
        Dict[str, Union[str, bool, List[Dict[str, str]]]]: A dictionary containing the fetched package data.
    """
    # Construct the URL for the PyPI API
    url = f"https://pypi.org/pypi/{package['package_name']}/json"

    # Log the URL being fetched
    logger.info(f"Fetching data from {url}")

    # Send a GET request to the PyPI API
    response = await client.get(url)

    # If the response status code is 200, extract the package data
    if response.status_code == 200:
        # Parse the response JSON
        data = response.json()

        # Extract the package info and vulnerabilities
        info = data["info"]
        vulnerabilities = data["vulnerabilities"]

        # Construct the package data dictionary
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

        # Log the fetched package data
        logger.debug(f"Fetched data for package {package_data}")

        # Return the package data
        return package_data


async def check_packages(packages: List[Dict[str, Union[str, bool]]]) -> List[Dict[str, Union[str, bool, List[Dict[str, str]]]]]:
    """
    Checks a list of packages for updates and vulnerabilities.

    This function iterates over each package in the list, fetching the package data from PyPI and checking for updates
    and vulnerabilities. The fetched package data includes the package name, current version, latest version,
    package URL, package description, vulnerabilities, home page, author, author email, license, and bracket-related info.

    Args:
        packages (List[Dict[str, Union[str, bool]]]): A list of packages, where each package is represented
        as a dictionary containing the package name, current version, and bracket-related info.

    Returns:
        List[Dict[str, Union[str, bool, List[Dict[str, str]]]]]: A list of dictionaries containing the fetched package data.
    """
    # Log the start of the function
    logger.info("Checking packages for updates and vulnerabilities")

    # Initialize the list of package data
    package_data_list = []

    # Create an HTTP client
    async with httpx.AsyncClient() as client:
        # Iterate over each package
        for package in packages:
            # Fetch the package data from PyPI
            package_data = await fetch_package_data(client, package)

            # Append the package data to the list
            package_data_list.append(package_data)

    # Log the successful check of packages
    logger.info("Packages checked successfully")

    # Return the list of package data
    return package_data_list

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


async def store_package_data(package_data: Dict[str, Union[str, bool, List[Dict[str, str]]]], request_group_id: str) -> None:
    """
    Stores package data in the database.

    This function checks if the library name already exists in the database. If it does not exist, a new LibraryName record
    is created. Then, a new Library record is created with the package data. The package data includes the package name,
    current version, latest version, package URL, package description, vulnerabilities, home page, author, author email,
    license, and bracket-related info.

    Args:
        package_data (Dict[str, Union[str, bool, List[Dict[str, str]]]]): A dictionary containing the package data.
        request_group_id (str): The ID of the request group.

    Returns:
        None
    """
    # Log the start of the function
    logger.debug(f"Starting store_package_data with package_data: {package_data} and request_group_id: {request_group_id}")

    # Check if the library name already exists in the database
    library_name_results = await db_ops.read_query(Select(LibraryName).where(LibraryName.name == package_data["package_name"]))

    if len(library_name_results) == 0:
        # If the library name does not exist, create a new LibraryName record
        library_name = LibraryName(name=package_data["package_name"])
        await db_ops.create_one(library_name)
        library_name_results = await db_ops.read_query(Select(LibraryName).where(LibraryName.name == package_data["package_name"]))

    # Extract the LibraryName object from the list
    library_name = library_name_results[0]

    # Create a new Library record with the package data
    library = Library(
        request_group_id=request_group_id,
        library_id=library_name.pkid,
        current_version=package_data["current_version"],
        new_version=package_data["latest_version"],
        new_version_vulnerability=bool(package_data["vulnerabilities"]),  # Set to True if vulnerabilities exist
        vulnerability=package_data["vulnerabilities"],
    )

    try:
        # Attempt to create the new Library record
        await db_ops.create_one(library)
        logger.debug(f"Successfully stored package data: {package_data}")
    except Exception as e:
        # Log any exceptions that occur
        logger.error(f"Failed to store package data: {package_data}. Error: {e}")

    # Log the end of the function
    logger.debug(f"Finished store_package_data with package_data: {package_data} and request_group_id: {request_group_id}")


