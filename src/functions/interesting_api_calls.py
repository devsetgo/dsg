# -*- coding: utf-8 -*-

import calendar
import datetime
import time

from httpx import AsyncClient
from loguru import logger
from unsync import unsync

client = AsyncClient()


async def get_public_debt():
    dates_list = []

    for year in range(1995, 2025):
        month = 1  # January
        month_calendar = calendar.monthcalendar(year, month)
        second_wednesday = (
            month_calendar[1][calendar.WEDNESDAY]
            if month_calendar[0][calendar.WEDNESDAY] != 0
            else month_calendar[2][calendar.WEDNESDAY]
        )
        date_str = f"{year}-{month:02d}-{second_wednesday:02d}"
        dates_list.append(date_str)

    current_date = datetime.datetime.now()
    days_to_subtract = (current_date.weekday() - 2) % 7 + 7
    last_wednesday = current_date - datetime.timedelta(days=days_to_subtract)
    last_wednesday_str = last_wednesday.strftime("%Y-%m-%d")
    dates_list.append(last_wednesday_str)
    dates_list.sort()
    t0 = time.time()

    # Assuming debt_api_call is an async function that makes API calls for each date
    tasks = [debt_api_call(date) for date in dates_list]
    debt_list = [task.result() for task in tasks]

    # Filter out None values from debt_list before sorting
    filtered_debt_list = [debt for debt in debt_list if debt is not None]

    logger.info(f"Debt API call time taken: {time.time() - t0:.3f} seconds")
    return sorted(filtered_debt_list, key=lambda d: d["record_date"])


@unsync
async def debt_api_call(debt_date: str):
    url = f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?filter=record_date:eq:{debt_date}"
    response = await client.get(url)
    resp = response.json()
    logger.debug(f"Debt API call response: {resp} for date {debt_date}")

    # Check if 'data' is not empty before accessing its first element
    if resp["data"]:
        return resp["data"][0]
    else:
        logger.warning(f"No data returned for date {debt_date}")
        return None  # Or handle the empty data case as needed
