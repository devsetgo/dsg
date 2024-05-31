# -*- coding: utf-8 -*-

import datetime
import time

from httpx import AsyncClient
from loguru import logger
from tqdm import tqdm
from unsync import unsync

client = AsyncClient()


async def get_public_debt():
    dates_list = [
        "2000-01-03",
        "2001-01-05",
        "2002-01-03",
        "2003-01-03",
        "2004-01-05",
        "2005-01-03",
        "2006-01-03",
        "2007-01-03",
        "2008-01-03",
        "2009-01-06",
        "2010-01-05",
        "2011-01-03",
        "2012-01-03",
        "2013-01-03",
        "2014-01-02",
        "2015-01-02",
        "2016-01-04",
        "2017-01-03",
        "2018-01-02",
        "2019-01-02",
        "2020-01-02",
        "2021-01-04",
        "2022-01-03",
        "2023-01-03",
        "2024-01-02",
    ]

    current_date = datetime.datetime.now()
    days_to_subtract = (current_date.weekday() - 2) % 7 + 7
    last_wednesday = current_date - datetime.timedelta(days=days_to_subtract)
    last_wednesday_str = last_wednesday.strftime("%Y-%m-%d")
    dates_list.append(last_wednesday_str)
    dates_list.sort()
    t0 = time.time()
    tasks = [
        debt_api_call(debt_date=d) for d in tqdm(dates_list, ascii=False, leave=True)
    ]
    debt_list = [task.result() for task in tasks]
    print(f"Debt API call time taken: {time.time() - t0:.3f}")
    return sorted(debt_list, key=lambda d: d["record_date"])


@unsync
async def debt_api_call(debt_date: str):

    url = f"https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/debt_to_penny?filter=record_date:eq:{debt_date}"
    response = await client.get(url)
    resp = response.json()
    logger.debug(f"Debt API call response: {resp} for date {debt_date}")
    return resp["data"][0]
