# -*- coding: utf-8 -*-
"""
date_functions.py

This module provides a function for converting a datetime object or string to a specified timezone.
It uses the pytz library to handle timezone conversions and the loguru library for logging.

Functions:
    timezone_update(user_timezone: str, date_time, friendly_string=False): Convert a datetime object or string to a specified timezone and optionally return it as a formatted string.
"""
from datetime import datetime

import pytz
from loguru import logger

TIMEZONES = pytz.all_timezones

async def timezone_update(user_timezone: str, date_time, friendly_string=False):
    """
    Convert a datetime object or string to a specified timezone and optionally return it as a formatted string.

    Args:
        user_timezone (str): The timezone to convert date_time to.
        date_time (datetime or str): The datetime object or string to convert.
        friendly_string (bool): If True, return date_time as a formatted string.

    Returns:
        datetime or str: The converted datetime. If friendly_string is True, this will be a string.
    """
    # Log the input parameters
    logger.debug(
        f"Updating timezone: {user_timezone}, date_time: {date_time}, friendly_string: {friendly_string}"
    )

    # If date_time is None, return None
    if date_time is None:
        return None

    # If date_time is a string, parse it into a datetime object
    if isinstance(date_time, str):
        date_time = datetime.fromisoformat(date_time)

    # Try to convert UTC date_time to user's timezone
    try:
        user_tz = pytz.timezone(user_timezone)
        date_time = date_time.astimezone(user_tz)
    except Exception as e:
        # Log any errors that occur when updating the timezone
        logger.error(f"Error updating timezone: {e}")
        raise

    # If friendly_string is True, convert date_time to a formatted string
    if friendly_string:
        date_time = date_time.strftime("%d %b, %Y %I:%M %p")

    # Log the updated date_time
    logger.debug(f"Updated date_time: {date_time}")

    return date_time
