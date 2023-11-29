# -*- coding: utf-8 -*-
# from pathlib import Path
import re
import uuid
from datetime import datetime

import httpx
from loguru import logger

from endpoints.pypi_check.crud import store_in_data
from endpoints.pypi_check.crud import store_lib_request

client = httpx.AsyncClient()


async def loop_calls_adv(itemList: list, request_group_id: str):
    """
    Given a list of dictionaries containing library names and their current versions,
    this function retrieves metadata from PyPI about those libraries such as their latest
    version number, whether they have vulnerabilities, etc. and stores those details in a
    dictionary for each library. The complete set of library dictionaries is stored in
    a list which is returned at the end.

    Args:
        itemList (list): A list of dictionaries containing the names and versions of libraries
        request_group_id (str): A unique identifier for the request group to which these libraries belong

    Returns:
        list: A list of dictionaries with details about each library in the same order as itemList
    """

    # Initialize an empty list to store the results
    results = []

    # Loop through each item dictionary in the given itemList
    for i in itemList:
        # Build the URL for the PyPI API request using the name of the current library
        url = f"https://pypi.org/pypi/{i['library']}/json"
        logger.info(f"call pypi url: {url}")
        # Make the API request using the above URL
        resp = await call_pypi_adv(url)

        # If the response is None (i.e. if there was some error) or "newVersion" is not in the response JSON,
        # then set new_version to "not found" and vulnerabilities to an empty list
        if resp is None or "newVersion" not in resp:
            new_version = "not found"
            vulnerabilities = []
        # Otherwise, extract the latest version number and vulnerabilities from the response JSON
        else:
            new_version = resp["newVersion"]
            vulnerabilities = resp.get("vulnerabilities", [])

        # Create a dictionary containing details about the current library
        pip_info = {
            "library": i["library"],
            "currentVersion": i["currentVersion"],
            "newVersion": new_version,
            "has_bracket": i["has_bracket"],
            "bracket_content": i["bracket_content"],
            "request_group_id": request_group_id,
            "vulnerbilities": vulnerabilities,
        }

        # Log a warning with the above dictionary
        logger.warning(pip_info)

        # Append the above dictionary to the results list
        results.append(pip_info)

        # Store the above dictionary in an external database
        await store_lib_request(json_data=pip_info, request_group_id=request_group_id)

    # Log an info statement with the complete set of collected information about all libraries
    logger.info(results)

    # Return the complete set of collected information about all libraries
    return results


async def call_pypi_adv(url):
    """
    An asynchronous function which takes a url and sends a GET request to it.

    Args:
        url: A string containing the url to send the GET request to.

    Returns:
        result: A dictionary containing the response data.
                If the status code is not 200 it will contain {"newVersion": "not found"}.
                Otherwise, it will contain the version info and vulnerabilities from the JSON response.
    """

    # Sends a GET request to the URL using the aiohttp client
    r = await client.get(url)

    if r.status_code != 200:
        # Set the newVersion to a string indicating that it was not found
        result = {"newVersion": "not found"}
    else:
        # Parse the JSON response
        resp = r.json()
        logger.warning(resp["vulnerabilities"])
        result = {
            "newVersion": resp["info"]["version"],
            "vulnerabilities": resp["vulnerabilities"],
        }
    return result


async def call_pypi_adv(url):
    """
    Calls an API with the given URL using a client. Returns the new version
    and vulnerabilities for the package.

    Args:
    url (str): A string indicating the url of the API

    Returns:
    result (dict): A dictionary containing new package version and
                   vulnerabilities.
    """
    # send a GET request to the API
    r = await client.get(url)

    if r.status_code != 200:
        # if no response, return not found
        result = {"newVersion": "not found"}
    else:
        # if response is valid, get necessary data from response
        resp = r.json()
        logger.warning(resp["vulnerabilities"])
        result = {
            "newVersion": resp["info"]["version"],
            "vulnerabilities": resp["vulnerabilities"],
        }

    # return the result
    return result


def pattern_between_two_char(text_string: str) -> list:
    """
    Finds the text contained within the first set of square brackets in the
    string.

    Args:
    text_string (str): A string containing square brackets around text.

    Returns:
    result (list): A list containing the text between the brackets.
    """
    # define a regular expression pattern to extract text between brackets
    pattern = "\[(.+?)\]+?"
    # search the input string for matches to the pattern
    result_list = re.findall(pattern, text_string)
    # select the first match
    result = result_list[0]
    # return the result
    return result


def clean_item(items: list) -> list:
    """
    Cleans up the input list and returns a new list of clean items.

    Args:
    items (list): A list of strings containing pip package names and versions.

    Returns:
    results (list): A list of cleaned pip packages that includes the library name, current version, whether it has
    brackets or not, and what's inside the brackets.
    """

    results: list = []

    for i in items:
        # Check if line starts with '#' or '-' and skip them.
        comment = i.startswith("#")
        recur_file = i.startswith("-")
        empty_line = False
        if i:
            empty_line = False

        # Skip lines with comments, recursion references, or empty lines.
        if (
            len(i.strip()) != 0
            and comment is False  # noqa
            and recur_file is False  # noqa
            and empty_line is False  # noqa
        ):
            logger.debug(i)

            # Initialize values.
            has_bracket = None
            bracket_content = None

            # Check if line contains []. If so, set has_bracket to True and get string inside [].
            if "[" in i:
                has_bracket = True
                logger.debug(has_bracket)
                bracket_content = pattern_between_two_char(i)
                logger.debug(bracket_content)

            # Replace signs before splitting.
            if "==" in i:
                new_i = i.replace("==", " ")
            elif ">=" in i:
                new_i = i.replace(">=", " ")
            elif "<=" in i:
                new_i = i.replace("<=", " ")
            elif ">" in i:
                new_i = i.replace(">", " ")
            elif "<" in i:
                new_i = i.replace("<", " ")
            else:
                new_i = i

            # Remove unnecessary text.
            cleaned_up_i = re.sub("[\(\[].*?[\)\]]", "", new_i)
            logger.debug(cleaned_up_i)

            # Split library name from version and get values.
            m = cleaned_up_i
            pipItem = m.split()
            logger.debug(pipItem)

            library = pipItem[0]
            try:
                currentVersion = pipItem[1]
            except Exception:
                currentVersion = "none"

            # Create dictionary with relevant information.
            cleaned_lib = {
                "library": library,
                "currentVersion": currentVersion,
                "has_bracket": has_bracket,
                "bracket_content": bracket_content,
            }

            logger.debug(cleaned_lib["library"])
            lib = cleaned_lib["library"]
            if not any(l["library"] == lib for l in results):  # noqa
                results.append(cleaned_lib)
    logger.debug(results)
    return results


async def process_raw(raw_data: str):
    """
    Processes raw data and returns a list of libraries to be checked.

    Args:
        raw_data (str): Raw data to be processed.

    Returns:
        A list of libraries to be checked.
    """

    req_list = list(raw_data.split("\r\n"))  # Split the raw data and create a list
    logger.debug(raw_data)

    new_req: list = []
    pattern = "^[a-zA-Z0-9]"

    # Check each item in the request list for valid library names and append it to the new_req list
    # in case of any invalid character, it will be skipped using else pass statement
    for r in req_list:
        if re.match(pattern, r):
            new_req.append(r)
            logger.info(f"library: {r}")
        else:
            pass

    return new_req


async def main(raw_data: str, request):
    """
    This function takes a string of raw data and a request object as input,
    processes the data by calling process_raw() and clean_item(), calls an
    external API using loop_calls_adv(), stores the input and output data,
    and returns the request group ID.

    Args:
        raw_data (str): A string containing the raw data to be processed.
        request (object): An object containing information about the HTTP request.

    Returns:
        A UUID representing the request group ID for the processed data.
    """

    # Generate a new UUID for the request group ID.
    request_group_id = uuid.uuid4()

    # Process the raw data using the process_raw() function and store the result in a list.
    req_list: list = await process_raw(raw_data=raw_data)

    # Clean the data using the clean_item() function and store the result in a list.
    cleaned_data: list = clean_item(req_list)

    # Call an external API using the loop_calls_adv() function and store the result in a dictionary.
    fulllist: dict = await loop_calls_adv(cleaned_data, str(request_group_id))

    # Create a dictionary containing information about the input and output data.
    # The dictionary includes a new UUID for the data, the request group ID, the raw input data,
    # the processed input data, the output data from the external API, the client's IP address,
    # the request headers, and the date and time the data was created.
    values = {
        "id": str(uuid.uuid4()),
        "request_group_id": str(request_group_id),
        "text_in": raw_data,
        "json_data_in": req_list,
        "json_data_out": fulllist,
        "host_ip": request.client.host,
        "header_data": dict(request.headers),
        "date_created": datetime.now(),
    }

    # Store the input and output data in a database using the store_in_data() function.
    await store_in_data(values)

    # Return the request group ID.
    return request_group_id
