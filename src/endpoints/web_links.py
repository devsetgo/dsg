# -*- coding: utf-8 -*-
"""
This module, `web_links.py`, serves as a part of a web application that showcases interesting weblinks, categorized and filterable by tags, date ranges, and categories. It utilizes FastAPI for routing and SQLAlchemy for database interactions, providing an API endpoint to list interesting weblinks with support for pagination.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating API routes and handling HTTP requests.
    - loguru: For logging.
    - sqlalchemy: For constructing and executing SQL queries.
    - datetime: For handling date and time information.
    - db_tables: Contains the SQLAlchemy table definitions for Categories and WebLinks.
    - functions: Includes utility functions and decorators, such as for AI processing and date manipulation.
    - resources: Provides access to common resources like database operations (`db_ops`) and HTML templates.

API Endpoints:
    - GET "/": Lists weblinks with optional filters applied. Supports pagination through `offset` and `limit` query parameters.
    - GET "/categories": Retrieves a list of categories for weblinks.
    - GET "/pagination": Lists weblinks with pagination and optional filters.
    - GET "/new": Displays a form to create a new interesting link.
    - POST "/new": Creates a new interesting link based on form data.


Usage:
    This module is designed to be integrated into a FastAPI application, providing a backend API for listing weblinks. It can be used in web applications that require content curation and discovery features, with the ability to filter and paginate through large sets of data.
"""
from datetime import datetime

# from pytz import timezone, UTC
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select, asc, func, or_

from ..db_tables import Categories, WebLinks
from ..functions import ai, date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()


# api endpoints
# /list with filters (by tag, by date range, by category)
@router.get("/")
async def list_of_web_links(
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(100, description="Limit for pagination"),
    # user_info: dict = Depends(check_login),
):
    user_timezone = request.session.get("timezone", None)
    if user_timezone is None:
        user_timezone = "America/New_York"

    query = Select(WebLinks).limit(10).offset(0)
    weblinks = await db_ops.read_query(query=query)

    if isinstance(weblinks, str):
        logger.error(f"Unexpected result from read_query: {weblinks}")
        weblinks = []
    else:
        weblinks = [link.to_dict() for link in weblinks]
    # offset date_created and date_updated to user's timezone
    for link in weblinks:
        link["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=link["date_created"],
            friendly_string=True,
        )
        link["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=link["date_updated"],
            friendly_string=True,
        )
    context = {"page": "weblinks", "request": request}#, "weblinks": weblinks}
    return templates.TemplateResponse(
        request=request, name="/weblinks/index.html", context=context
    )


@router.get("/categories", response_class=JSONResponse)
async def get_categories():
    categories = await db_ops.read_query(
        Select(Categories)
        .where(Categories.is_weblink == True)
        .order_by(asc(func.lower(Categories.name)))
    )
    cat_list = [cat.to_dict()["name"] for cat in categories]
    return cat_list


@router.get("/pagination")
async def read_weblinks_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    category: str = Query(None, description="Category"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(10, description="Number of weblinks per page"),
    # user_info: dict = Depends(check_login),
):
    query_params = {
        "search_term": search_term,
        "start_date": start_date,
        "end_date": end_date,
        "category": category,
        "limit": limit,
    }

    user_timezone = request.session.get("timezone", None)
    if user_timezone is None:
        user_timezone = "America/New_York"

    logger.info(
        f"Searching for term: {search_term}, start_date: {start_date}, end_date: {end_date}"
    )
    # find search_term in columns: note, mood, tags, summary
    query = Select(WebLinks).where(
        or_(
            WebLinks.name.contains(search_term) if search_term else True,
            (
                WebLinks.description.contains(search_term)
                if search_term
                else True
            ),
        )
    )

    # filter by date range
    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(
            (WebLinks.date_created >= start_date)
            & (WebLinks.date_created <= end_date)
        )
    # order and limit the results
    offset = (page - 1) * limit
    query = (
        query.order_by(WebLinks.date_created.desc())
        .limit(limit)
        .offset(offset)
    )
    weblinks = await db_ops.read_query(query=query)
    logger.debug(f"weblinks returned from pagination query {weblinks}")
    if isinstance(weblinks, str):
        logger.error(f"Unexpected result from read_query: {weblinks}")
        weblinks = []
    else:
        weblinks = [link.to_dict() for link in weblinks]
    # offset date_created and date_updated to user's timezone
    for link in weblinks:
        link["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=link["date_created"],
            friendly_string=True,
        )
        link["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=link["date_updated"],
            friendly_string=True,
        )
    found = len(weblinks)
    count_query = Select(WebLinks)
    weblinks_count = await db_ops.count_query(query=count_query)

    current_count = found

    total_pages = -(-weblinks_count // limit)  # Ceiling division
    # Generate the URLs for the previous and next pages
    prev_page_url = (
        f"/weblinks/pagination?page={page - 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page > 1
        else None
    )
    next_page_url = (
        f"/weblinks/pagination?page={page + 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page < total_pages
        else None
    )
    logger.info(f"Found {found} weblinks")
    context={"page": "weblinks",
            "weblinks": weblinks,
            "found": found,
            "weblinks_count": weblinks_count,
            "total_pages": total_pages,
            "start_count": offset + 1,
            "current_count": offset + current_count,
            "current_page": page,
            "prev_page_url": prev_page_url,
            "next_page_url": next_page_url,
        }
    return templates.TemplateResponse(
        request=request,
        name="/weblinks/pagination.html",
        context=context,
    )


@router.get("/new")
async def new_link(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="/weblinks/new.html",
        context={"page": "weblinks","request": request},
    )


@router.post("/new")
async def create_link(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]

    form = await request.form()
    category = form["category"]
    url = form["url"]
    title = form["title"]

    logger.debug(f"Received category: {category} and content: {url}")

    # Get summary from OpenAI
    summary = await ai.get_url_summary(url=url, sentence_length=2)
    logger.debug(f"Received summary from AI: {summary}")
    # Create the post
    link = WebLinks(
        title=title,
        summary=summary,
        user_id=user_identifier,
        category=category,
    )
    data = await db_ops.create_one(link)
    if isinstance(data, dict):
        logger.error(f"Error creating link: {data}")
        return RedirectResponse(url="/error/418", status_code=302)

    logger.debug(f"Created weblinks: {link}")
    logger.info(f"Created weblinks with ID: {data.pkid}")

    return RedirectResponse(url=f"/weblink/view/{data.pkid}", status_code=302)


