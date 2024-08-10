# -*- coding: utf-8 -*-
"""
This module contains functions to interact with various public APIs and
perform operations related to API metrics.

Functions:
    get_public_debt: Fetches public debt data for specific dates and checks for updated metrics.

Modules:
    calendar: Provides functions related to calendar operations.
    datetime: Supplies classes for manipulating dates and times.
    time: Provides various time-related functions.
    httpx.AsyncClient: Used for making asynchronous HTTP requests.
    loguru.logger: Used for logging.
    sqlalchemy.Select: Used for constructing SQL SELECT statements.
    unsync: Provides a decorator for running functions asynchronously.
    db_tables.APIMetrics: Contains database table definitions for API metrics.
    resources.db_ops: Contains database operations related to API metrics.

Author:
    Mike Ryan
    MIT Licensed
"""
import calendar
import datetime
import time
from typing import Dict, List, Optional

from httpx import AsyncClient
from loguru import logger
from sqlalchemy import select
from unsync import unsync

from ..db_tables import APIMetrics
from ..resources import db_ops

client = AsyncClient()


async def get_public_debt() -> Optional[List[Dict[str, str]]]:
    """
    Fetches public debt data for specific dates and checks for updated metrics.

    This function checks if there are existing metrics for the "debt_to_penny" API.
    If no existing metrics are found, it generates a list of dates for the second
    Wednesday of January from 1995 to 2024. It also calculates the date of the
    most recent Wednesday and makes API calls for each date to fetch public debt data.
    The fetched data is then saved to the database.

    Returns:
        Optional[List[Dict[str, str]]]: A list of dictionaries containing the public debt data,
        or None if no data is available.
    """
    dates_list: List[str] = []

    # Check for existing metrics
    existing: Optional[Dict[str, str]] = await check_for_updated_metrics(api_name="debt_to_penny")

    if existing is None:
        # Generate dates for the second Wednesday of January from 1995 to 2024
        for year in range(1995, 2025):
            month: int = 1  # January
            month_calendar: List[List[int]] = calendar.monthcalendar(year, month)
            second_wednesday: int = (
                month_calendar[1][calendar.WEDNESDAY]
                if month_calendar[0][calendar.WEDNESDAY] != 0
                else month_calendar[2][calendar.WEDNESDAY]
            )
            date_str: str = f"{year}-{month:02d}-{second_wednesday:02d}"
            dates_list.append(date_str)

        # Calculate the date of the most recent Wednesday
        current_date: datetime.datetime = datetime.datetime.now()
        days_to_subtract: int = (current_date.weekday() - 2) % 7 + 7
        last_wednesday: datetime.datetime = current_date - datetime.timedelta(days=days_to_subtract)
        last_wednesday_str: str = last_wednesday.strftime("%Y-%m-%d")
        dates_list.append(last_wednesday_str)
        dates_list.sort()
        t0: float = time.time()

        # Assuming debt_api_call is an async function that makes API calls for each date
        tasks = [debt_api_call(date) for date in dates_list]
        debt_list = [task.result() for task in tasks]

        # Filter out None values from debt_list before sorting
        filtered_debt_list: List[Dict[str, str]] = [debt for debt in debt_list if debt is not None]

        logger.info(f"Debt API call time taken: {time.time() - t0:.3f} seconds")

        # Sort the data by record_date
        data: List[Dict[str, str]] = sorted(filtered_debt_list, key=lambda d: d["record_date"])

        # Save the data to the database
        api_data: APIMetrics = APIMetrics(api_name="debt_to_penny", metric_data=data)
        result: bool = await db_ops.create_one(api_data)
        logger.debug(f"Data saved to database: {result}")
    else:
        data = existing["metric_data"]
        logger.debug(f"Data retrieved from database: {data}")

    return data


@unsync
async def debt_api_call(debt_date: str) -> Optional[Dict[str, str]]:
    """
    Makes an API call to fetch public debt data for a specific date.

    This function constructs a URL to query the "debt_to_penny" API for a given date.
    It then makes an asynchronous HTTP GET request to fetch the data. If the response
    contains data and the status code is 200, it returns the first element of the data.
    Otherwise, it logs a warning or error and returns None.

    Args:
        debt_date (str): The date for which to fetch the public debt data in the format 'YYYY-MM-DD'.

    Returns:
        Optional[Dict[str, str]]: A dictionary containing the public debt data for the specified date,
        or None if no data is available or an error occurs.
    """
    url: str = f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?filter=record_date:eq:{debt_date}"

    try:
        # Make an asynchronous HTTP GET request
        response = await client.get(url)
        resp: Dict = response.json()
        logger.debug(f"Debt API call response: {resp} for date {debt_date}")

        # Check if 'data' is not empty before accessing its first element
        if resp["data"] and response.status_code == 200:
            return resp["data"][0]
        else:
            logger.warning(f"No data returned for date {debt_date}")
            return None  # Handle the empty data case as needed
    except Exception as e:
        logger.error(f"Error getting debt data for date {debt_date}: {e}")
        return None


async def check_for_updated_metrics(api_name: str) -> Optional[Dict[str, str]]:
    """
    Checks if there are updated metrics for a given API name.

    This function queries the database for metrics associated with the specified API name.
    If metrics are found, it checks if the data is less than 24 hours old. If the data is
    recent, it returns the metrics; otherwise, it returns None.

    Args:
        api_name (str): The name of the API for which to check updated metrics.

    Returns:
        Optional[Dict[str, str]]: A dictionary containing the metrics data if it is less than
        24 hours old, or None if no data is found or the data is outdated.
    """
    # Query the database for metrics associated with the specified API name
    data: Optional[List[APIMetrics]] = await db_ops.read_query(
        select(APIMetrics).where(APIMetrics.api_name == api_name)
    )

    if data:
        # Convert the first result to a dictionary
        data_dict: Dict[str, str] = data[0].to_dict()
        last_updated: datetime.datetime = data_dict["date_updated"]
        current_date: datetime.datetime = datetime.datetime.now()
        time_diff: datetime.timedelta = current_date - last_updated

        # Check if the data is less than 24 hours old
        if time_diff.total_seconds() < 86400:
            logger.info(f"Data is less than 24 hours old for api_name: {api_name}")
            return data_dict
        else:
            logger.info(f"Data is more than 24 hours old for api_name: {api_name}")
            return None
    else:
        logger.info(f"No data found for api_name: {api_name}")
        return None
