# -*- coding: utf-8 -*-
"""
pypi_metrics.py

This module contains functions for fetching and analyzing metrics related to PyPI (Python Package Index) packages.

It includes the following functions:
- get_pypi_metrics: Fetches various metrics such as the total number of libraries, the most common libraries,
    and the number of libraries per request group.

The metrics are fetched from a database using the sqlalchemy library. The results are then returned as a dictionary.

This module uses the fastapi library for creating an API router, the loguru library for logging, and the sqlalchemy library
for interacting with the database. It also uses the collections library for counting elements.
"""
from typing import Dict, List, Optional, Tuple, Union

from fastapi import APIRouter
from loguru import logger
from sqlalchemy import Select, func

from ..db_tables import Library, LibraryName, Requirement
from ..resources import db_ops

router = APIRouter()


async def get_pypi_metrics() -> Dict[str, Union[List, List[Tuple[str, int]], int]]:
    """
    Fetches various metrics related to PyPI packages.

    This function fetches the total number of libraries, the most common libraries, the number of libraries per request group,
    libraries with new versions, total requirements, requirements by host IP, most common user agents, last one hundred requests,
    and library names. The metrics are fetched from a database using the sqlalchemy library. The results are then returned as a dictionary.

    Returns:
        Dict[str, Union[List, List[Tuple[str, int]], int]]: A dictionary containing the fetched metrics.
    """
    # Initialize the metrics
    total_libraries = []
    most_common_libraries = []
    libraries_per_request_group = []
    libraries_with_new_versions = []
    total_requirements = []
    requirements_by_host_ip = []
    most_common_user_agents = []
    last_one_hundred_requests = []
    library_name = []

    try:
        # Fetch the total number of libraries
        total_libraries = await db_ops.count_query(query=Select(LibraryName))
    except Exception as e:
        logger.error(f"Error in total_libraries: {e}")

    try:
        # Fetch the most common libraries
        most_common_libraries = await most_common_library()
    except Exception as e:
        logger.error(f"Error in most_common_libraries: {e}")

    try:
        # Fetch the number of libraries per request group
        libraries_per_request_group = await db_ops.count_query(
            query=Select(Library.request_group_id)
            .group_by(Library.request_group_id)
            .order_by(func.count(Library.request_group_id).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in libraries_per_request_group: {e}")

    try:
        # Fetch libraries with new versions
        libraries_with_new_versions = await db_ops.count_query(
            query=Select(Library).where(Library.current_version != Library.new_version)
        )
    except Exception as e:
        logger.error(f"Error in libraries_with_new_versions: {e}")

    try:
        # Fetch total requirements
        total_requirements = await db_ops.count_query(query=Select(Requirement))
    except Exception as e:
        logger.error(f"Error in total_requirements: {e}")

    try:
        # Fetch requirements by host IP
        requirements_by_host_ip = await db_ops.count_query(
            query=Select(Requirement.host_ip)
            .group_by(Requirement.host_ip)
            .order_by(func.count(Requirement.host_ip).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in requirements_by_host_ip: {e}")

    try:
        # Fetch most common user agents
        most_common_user_agents = await db_ops.count_query(
            query=Select(Requirement.user_agent)
            .group_by(Requirement.user_agent)
            .order_by(func.count(Requirement.user_agent).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in most_common_user_agents: {e}")

    try:
        # Fetch last one hundred requests
        last_one_hundred_requests = [
            requirement.to_dict()
            for requirement in await db_ops.read_query(
                query=Select(Requirement)
                .order_by(Requirement.date_created.desc())
                .limit(1)
            )
        ]
    except Exception as e:
        logger.error(f"Error in last_one_hundred_requests: {e}")

    try:
        # Fetch library names
        library_name = [
            library.to_dict()
            for library in await db_ops.read_query(query=Select(LibraryName).limit(100))
        ]
    except Exception as e:
        logger.error(f"Error in library_name: {e}")

    # Return the fetched metrics
    return {
        "total_libraries": total_libraries,
        "libraries_per_request_group": libraries_per_request_group,
        "libraries_with_new_versions": libraries_with_new_versions,
        "total_requirements": total_requirements,
        "requirements_by_host_ip": requirements_by_host_ip,
        "most_common_user_agents": most_common_user_agents,
        "average_number_of_libraries_per_requirement": await average_number_of_libraries_per_requirement(),
        "total_number_of_vulnerabilities": await number_of_vulnerabilities(),
        "most_common_libraries": most_common_libraries,
        "libraries_with_most_vulnerabilities": await get_libraries_with_most_vulnerabilities(),
        "last_one_hundred_requests": last_one_hundred_requests,
        "library_name": library_name,
    }


async def get_libraries_with_most_vulnerabilities() -> List[Tuple[str, int]]:
    """
    Fetches the libraries with the most vulnerabilities.

    This function fetches the libraries that have the most vulnerabilities from a database using the sqlalchemy library.
    The results are then returned as a list of tuples, where each tuple contains a library name and the number of vulnerabilities it has.

    Returns:
        List[Tuple[str, int]]: A list of tuples, where each tuple contains a library name and the number of vulnerabilities it has.
    """
    # Initialize the list of libraries with the most vulnerabilities
    libraries_with_most_vulnerabilities = []

    try:
        # Fetch the libraries with the most vulnerabilities
        libraries_with_most_vulnerabilities = await db_ops.read_query(
            query=Select(Library.name, func.count(Vulnerability.id))
            .join(Vulnerability)
            .group_by(Library.name)
            .order_by(func.count(Vulnerability.id).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in get_libraries_with_most_vulnerabilities: {e}")

    # Return the list of libraries with the most vulnerabilities
    return libraries_with_most_vulnerabilities


async def get_libraries_with_most_vulnerabilities() -> List[Tuple[str, int]]:
    """
    Fetches the libraries with the most vulnerabilities.

    This function fetches the libraries that have the most vulnerabilities from a database using the sqlalchemy library.
    The results are then returned as a list of tuples, where each tuple contains a library name and the number of vulnerabilities it has.

    Returns:
        List[Tuple[str, int]]: A list of tuples, where each tuple contains a library name and the number of vulnerabilities it has.
    """
    # Initialize the list of libraries with the most vulnerabilities
    libraries_with_most_vulnerabilities = []

    try:
        # Fetch the libraries with the most vulnerabilities
        libraries_with_most_vulnerabilities = await db_ops.read_query(
            query=Select(Library.name, func.count(Vulnerability.id))
            .join(Vulnerability)
            .group_by(Library.name)
            .order_by(func.count(Vulnerability.id).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in get_libraries_with_most_vulnerabilities: {e}")

    # Return the list of libraries with the most vulnerabilities
    return libraries_with_most_vulnerabilities


async def most_common_library() -> List[Tuple[str, int]]:
    """
    Fetches the most common libraries.

    This function fetches the libraries that are most commonly used from a database using the sqlalchemy library.
    The results are then returned as a list of tuples, where each tuple contains a library name and the number of times it is used.

    Returns:
        List[Tuple[str, int]]: A list of tuples, where each tuple contains a library name and the number of times it is used.
    """
    # Initialize the list of most common libraries
    most_common_libraries = []

    try:
        # Fetch the most common libraries
        most_common_libraries = await db_ops.read_query(
            query=Select(Library.name, func.count(Library.id))
            .group_by(Library.name)
            .order_by(func.count(Library.id).desc())
            .limit(10)
        )
    except Exception as e:
        logger.error(f"Error in most_common_library: {e}")

    # Return the list of most common libraries
    return most_common_libraries



async def average_number_of_libraries_per_requirement() -> Optional[float]:
    """
    Calculates the average number of libraries per requirement.

    This function fetches the first 100,000 libraries from a database using the sqlalchemy library. It then calculates the average number of libraries per requirement
    by dividing the total number of libraries by the total number of requirements. The result is then returned.

    Returns:
        Optional[float]: The average number of libraries per requirement, or None if there are no requirements.
    """
    # Log the start of the function
    logger.info("Starting average_number_of_libraries_per_requirement")

    # Query the Library table for entries
    # This query will fetch the first 100,000 entries from the Library table
    logger.debug("Querying the Library table")
    libraries: List[Dict] = await db_ops.read_query(query=Select(Library).limit(100000))

    # Convert each Library object to a dictionary
    # This is done to make it easier to access the properties of each Library object
    logger.debug("Converting Library objects to dictionaries")
    libraries = [library.to_dict() for library in libraries]

    # Calculate the total number of libraries
    total_libraries = len(libraries)

    # Calculate the total number of requirements
    total_requirements = sum([len(library['requirements']) for library in libraries])

    # Calculate the average number of libraries per requirement
    # If there are no requirements, return None
    average = total_libraries / total_requirements if total_requirements else None

    # Return the average number of libraries per requirement
    return average
