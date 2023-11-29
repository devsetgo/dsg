# -*- coding: utf-8 -*-
import collections

from loguru import logger

from com_lib import crud_ops
from com_lib.db_setup import libraries
from com_lib.db_setup import requirements


async def get_data():
    query = libraries.select()

    try:
        data = await crud_ops.fetch_all_db(query=query)
    except Exception as e:
        logger.critical(f"DB Fetch Failure: {e}")
        return {"error": f"DB Fetch Failure: {e}"}

    try:
        lib_data_month = await process_by_month(data)
    except Exception as e:
        logger.critical(f"Process by Month Failure: {e}")
        return {"error": f"Process by Month Failure: {e}"}

    try:
        lib_sum = await sum_lib(lib_data_month)
    except Exception as e:
        logger.critical(f"Lib Sum Failure: {e}")
        return {"error": f"Lib Sum Failure: {e}"}

    try:
        library_data_count = await process_by_lib(data)
    except Exception as e:
        logger.critical(f"Process by Lib Failure: {e}")
        return {"error": f"Process by Lib Failure: {e}"}

    try:
        lib_data_sum = await sum_lib_count(library_data_count)
    except Exception as e:
        logger.critical(f"Lib Data Sum Failure: {e}")
        return {"error": f"Lib Data Sum Failure: {e}"}

    try:
        lib_new_ver = await lib_new_versions(data)
    except Exception as e:
        logger.critical(f"Lib New Version Failure: {e}")
        return {"error": f"Lib New Version Failure: {e}"}

    try:
        unique = await requests_data()
    except Exception as e:
        logger.critical(f"data requests_data error: {e}")
        return {"error": f"data requests_data error: {e}"}

    try:
        latest = await latest_results()
    except Exception as e:
        logger.critical(f"data requests_data error: {e}")
        return {"error": f"data requests_data error: {e}"}

    result = {
        "lib_data_month": lib_data_month,
        "lib_sum": lib_sum,
        "library_data_count": library_data_count,
        "lib_data_sum": lib_data_sum,
        "lib_new_ver": lib_new_ver,
        "unique": unique,
        "latest": latest,
    }
    logger.debug(f"pypi dashboard get_data result: {result}")
    return result


async def lib_new_versions(data: dict):
    ver = []
    for d in data:
        lib_ver = f'{d["library"]}={d["newVersion"]}'
        if lib_ver not in ver:
            ver.append(lib_ver)
    result = len(ver)
    logger.debug(f"lib_new_versions: {result}")
    return result


async def process_by_month(data: list) -> dict:
    """
    This function takes in a dictionary of data where each item contains a 'date_created' field,
    counts the number of items by month, and returns a dictionary of the form {'YYYY-MM': count}.

    :param data: A list of dictionaries where each dictionary contains a 'date_created' field.
    :return: A dictionary of the form {'YYYY-MM': count} where 'count' is the number of items created
             in that month.
    """

    # initialize a dictionary to store the results
    result: dict = {}
    if len(data) == 0:
        result["1900-01"] = 0
    # iterate over each item in the input data
    for d in data:
        # print(d)
        # extract the date_created field from the current item
        date_item = d["date_created"]

        # convert the date to a string of the form 'YYYY-MM'
        ym = date_item.strftime("%Y-%m")
        # update the count for this month in the result dictionary
        if ym not in result:
            result[
                ym
            ] = 1  # add new key-value pair if the month is not present in the result dictionary
        else:
            result[
                ym
            ] += 1  # increment value counter of existing key in the result dictionary

    # print out the result and return it
    logger.debug(f"process_by_month: {result}")  # log the result to debug
    return result


async def sum_lib(data: dict):
    """
    A function that takes a dictionary of library counts as input and returns their total count.

    Args:
    - data (dict): A dictionary containing the count of each library

    Returns:
    - result (int): An integer representing the total count of all libraries

    """
    # print(data)
    # Calculate the total count of all libraries
    result: int = sum(data.values())

    # Log the calculated result using a debug log level
    logger.debug(f"sum_lib: {result}")

    # Return the calculated result
    return result


async def process_by_lib(data: dict) -> dict:
    """
    A function that processes a dictionary object containing information about libraries and returns a new dictionary
    with the count of each library and how often it was checked along with the number of versions of the library.

    Args:
    - data (dict): A dictionary object containing information about libraries

    Returns:
    - result (dict): A dictionary object containing the library name, count, number of versions and check frequency
      of the most common 25 libraries

    """

    # Create an empty list to store the names of all libraries present in the input dictionary
    library_list = []

    # Loop through each dictionary in the input data and append the name of the library to the library_list
    for d in data:
        library_list.append(d["library"])

    # Use collections.Counter() method to count the occurrence of each library in the library_list,
    # take the 25 most common elements, and create a new dictionary with the count, number of versions,
    # and check frequency of the most common 25 libraries.
    result: dict = dict(collections.Counter(library_list).most_common(25))

    # Log the calculated result using a debug log level
    logger.debug(f"process_by_lib: {result}")

    # Return the calculated result
    return result


async def sum_lib_count(data: dict):
    """
    A function that takes a dictionary of libraries as input and returns their total count.

    Args:
    - data (dict): A dictionary containing the count of each library

    Returns:
    - result (int): An integer representing the total count of all libraries

    """

    # Calculate the total count of all libraries
    result: int = sum(data.values())

    # Log the calculated result using a debug log level
    logger.debug(f"sum_lib_count: {result}")

    # Return the calculated result
    return result


async def requests_data():
    """
    This function retrieves data from the requirements table in a database and calculates the number of
    unique IPs in the host_ip field. It returns a dictionary containing this information.

    :return: A dictionary with keys "unique" and "fulfilled", representing the total number of unique IPs
    and total number of fulfilled requirements, respectively.
    """

    # Define a SQL query to select all rows from the requirements table in a database.
    query = requirements.select()

    # Fetch all rows from the requirements table using fetch_all_db() function and store it in variable data.
    # The result returned is a list of dictionaries.
    data = await crud_ops.fetch_all_db(query=query)

    # Create an empty list to hold unique IP addresses.
    unique_ips = []

    # Loop through each row of data, check its host_ip field for uniqueness,
    # and add it to the unique_ips list if it's not found.
    for d in data:
        if d["host_ip"] not in unique_ips:
            unique_ips.append(d["host_ip"])

    fulfilled = len(data)
    # Finally, calculate the length of the unique_ips list and data list,
    # then return them as values in a dictionary.
    result = {"unique": len(unique_ips), "fulfilled": fulfilled}

    # Log the resulting dictionary into the debug logs.
    logger.debug(result)

    return result


async def latest_results():
    """
    A function that returns the latest 100 entries from a database table called 'requirements' sorted in descending order of date_created.

    Args:
    - None

    Returns:
    - data (list): A list of the latest 100 entries from the 'requirements' table in the database.

    """

    # Create an empty list called data.
    data = []

    # Commented out code for selecting and ordering columns from the 'requirements' table in the database.
    query = (
        requirements.select().limit(100).order_by(requirements.c.date_created.desc())
    )
    data = await crud_ops.fetch_all_db(query=query)

    # Log the value of the 'data' variable using a debug log level.
    logger.debug(data)

    # Return the value of the 'data' variable which should contain the latest 100 entries from the 'requirements' table.
    return data
