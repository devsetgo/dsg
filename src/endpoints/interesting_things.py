# -*- coding: utf-8 -*-
from datetime import datetime

# from pytz import timezone, UTC
from fastapi import APIRouter, Depends, Query, Request
from loguru import logger
from sqlalchemy import Select, or_

from ..db_tables import InterestingThings
from ..functions import date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()


# api endpoints
# /list with filters (by tag, by date range, by category)
@router.get("/")
async def list_of_interesting_things(
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(100, description="Limit for pagination"),
    # user_info: dict = Depends(check_login),
):
    user_timezone = request.session.get("timezone", None)
    if user_timezone is None:
        user_timezone = "America/New_York"

    query = Select(InterestingThings).limit(20).offset(0)
    things = await db_ops.read_query(query=query)

    if isinstance(things, str):
        logger.error(f"Unexpected result from read_query: {things}")
        things = []
    else:
        things = [thing.to_dict() for thing in things]
    # offset date_created and date_updated to user's timezone
    for thing in things:
        thing["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=thing["date_created"],
            friendly_string=True,
        )
        thing["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=thing["date_updated"],
            friendly_string=True,
        )
    context = {"request": request, "things": things}
    return templates.TemplateResponse(
        request=request, name="/posts/index.html", context=context
    )


@router.get("/pagination")
async def read_things_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    category: str = Query(None, description="Category"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(20, description="Number of notes per page"),
    user_info: dict = Depends(check_login),
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
    query = Select(InterestingThings).where(
        or_(
            InterestingThings.name.contains(search_term) if search_term else True,
            (
                InterestingThings.description.contains(search_term)
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
            (InterestingThings.date_created >= start_date)
            & (InterestingThings.date_created <= end_date)
        )
    # order and limit the results
    query = query.order_by(InterestingThings.date_created.desc())
    offset = (page - 1) * limit
    things = await db_ops.read_query(query=query, limit=limit, offset=offset)
    logger.debug(f"notes returned from pagination query {things}")
    if isinstance(things, str):
        logger.error(f"Unexpected result from read_query: {things}")
        things = []
    else:
        things = [thing.to_dict() for thing in things]
    # offset date_created and date_updated to user's timezone
    for thing in things:
        thing["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=thing["date_created"],
            friendly_string=True,
        )
        thing["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=thing["date_updated"],
            friendly_string=True,
        )
    found = len(things)
    things_count = await db_ops.count_query(query=query)

    current_count = found

    total_pages = -(-things_count // limit)  # Ceiling division
    # Generate the URLs for the previous and next pages
    prev_page_url = (
        f"/posts/pagination?page={page - 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page > 1
        else None
    )
    next_page_url = (
        f"/posts/pagination?page={page + 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page < total_pages
        else None
    )
    logger.info(f"Found {found} interesting things")
    return templates.TemplateResponse(
        request=request,
        name="/notes/pagination.html",
        context={
            "things": things,
            "found": found,
            "note_count": things_count,
            "total_pages": total_pages,
            "current_count": current_count,
            "current_page": page,
            "prev_page_url": prev_page_url,
            "next_page_url": next_page_url,
        },
    )


# get /item/{id}

# post (edit) /item/{id}

# post (delete) /delete/{id}

#
