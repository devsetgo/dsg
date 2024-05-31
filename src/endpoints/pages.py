# -*- coding: utf-8 -*-

import datetime
import time
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy import Select
from httpx import AsyncClient
from ..db_tables import InterestingThings, Posts
from ..resources import db_ops, templates
from ..settings import settings
from unsync import unsync
from tqdm import tqdm

router = APIRouter()
client = AsyncClient()


# create index page route
@router.get("/", response_class=RedirectResponse)
async def root():
    """
    Root endpoint of API
    Returns:
        Redrects to openapi document
    """
    # redirect to openapi docs
    logger.info("Redirecting to OpenAPI docs")
    return RedirectResponse(url="/pages/index")


@router.get("/index")
async def index(request: Request):
    cool_stuff = await db_ops.read_query(
        Select(InterestingThings)
        .limit(8)
        .order_by(InterestingThings.date_created.desc())
    )
    cool_stuff = [thing.to_dict() for thing in cool_stuff]
    posts = await db_ops.read_query(
        Select(Posts).limit(5).order_by(Posts.date_created.desc())
    )
    posts = [post.to_dict() for post in posts]
    context = {"data": {"my_stuff": {}, "cool_stuff": cool_stuff}, "posts": posts}

    return templates.TemplateResponse(
        request=request, name="index2.html", context=context
    )


@router.get("/about")
async def about_page(request: Request):
    """
    This function handles requests to the /about URL. It calls the `call_github_repos` and `call_github_user`
    functions to retrieve data from GitHub, and then returns a template response containing that data.

    Args:
        request: The incoming HTTP request object.

    Returns:
        A `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    """

    from ..functions.github import call_github_repos, call_github_user

    # Retrieve data from GitHub using the `call_github_repos` and `call_github_user` functions.
    data_repo = await call_github_repos()
    data_user = await call_github_user()

    # Combine the retrieved data into a single dictionary.
    data: dict = {
        "data_repo": data_repo,
        "data_user": data_user,
        "repo_name": settings.github_id,
    }

    # Define the name of the HTML template to use for this page.
    template: str = "about.html"

    # Define the context variables to pass to the template.
    context = {"data": data}

    # Log some information about the request.
    logger.info(f"page accessed: /{template}")
    logger.debug(dict(request.headers))

    # Return a `TemplateResponse` object containing the rendered HTML template and the retrieved data.
    return templates.TemplateResponse(request=request, name=template, context=context)


# login to site
@router.get("/login")
async def login(request: Request):
    context = {}
    return templates.TemplateResponse(
        request=request, name="users/login.html", context=context
    )


@router.get("/public-debt")
async def public_debt(request: Request):
    debt_list = await get_public_debt()

    last_year = None
    for d in debt_list:
        year_hold = d["tot_pub_debt_out_amt"]
        
        if d["debt_held_public_amt"] != 'null':
            d["debt_held_public_amt"] = "{:,.2f}".format(float(d["debt_held_public_amt"]))
        
        if d["intragov_hold_amt"] != 'null':
            d["intragov_hold_amt"] = "{:,.2f}".format(float(d["intragov_hold_amt"]))
        
        d["tot_pub_debt_out_amt"] = "{:,.2f}".format(float(d["tot_pub_debt_out_amt"]))

        if last_year is not None:
            d["debt_growth"] = "{:,.2f}".format(float(year_hold) - float(last_year))
            last_year = year_hold
        else:
            last_year = year_hold
    context = {"debt": debt_list}
    return templates.TemplateResponse(
        request=request, name="interesting-data.html", context=context
    )


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
