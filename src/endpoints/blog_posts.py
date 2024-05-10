# -*- coding: utf-8 -*-
import csv
import io
from datetime import UTC, datetime, timedelta

# from pytz import timezone, UTC
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pytz import timezone
from sqlalchemy import Select, Text, and_, asc, between, cast, extract, or_

from ..db_tables import Categories, Posts
from ..functions import ai, date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


# api endpoints
# /list with filters (by tag, by date range, by category)
@router.get("/")
async def list_of_posts(
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(100, description="Limit for pagination"),
    # user_info: dict = Depends(check_login),
):

    user_timezone = request.session.get("timezone", None)
    if user_timezone is None:
        user_timezone = "America/New_York"

    query = Select(Posts).limit(20).offset(0)
    posts = await db_ops.read_query(query=query)

    if isinstance(posts, str):
        logger.error(f"Unexpected result from read_query: {posts}")
        posts = []
    else:
        posts = [post.to_dict() for post in posts]
    # offset date_created and date_updated to user's timezone
    for post in posts:
        post["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=post["date_created"],
            friendly_string=True,
        )
        post["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=post["date_updated"],
            friendly_string=True,
        )
    context = {"request": request, "posts": posts}
    return templates.TemplateResponse(
        request=request, name="/posts/index.html", context=context
    )


@router.get("/categories", response_class=JSONResponse)
async def get_categories():
    categories = await db_ops.read_query(Select(Categories).order_by(asc(Categories.name)))
    cat_list = [cat.to_dict()['name'] for cat in categories]
    return cat_list


@router.get("/pagination")
async def read_posts_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    category: str = Query(None, description="Category"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(20, description="Number of posts per page"),
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
        f"Searching for term: {search_term}, start_date: {start_date}, end_date: {end_date}, category: {category}, user_timezon: {user_timezone}"
    )
    # find search_term in columns: note, mood, tags, summary
    query = Select(Posts).where(
        or_(
            Posts.title.contains(search_term) if search_term else True,
            Posts.content.contains(search_term) if search_term else True,
        )
    )

    # filter by category
    print(category)
    if category is not None:
        query = query.where(Posts.category == category.lower())
    # filter by date range
    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(
            (Posts.date_created >= start_date)
            & (Posts.date_created <= end_date)
        )
    # order and limit the results
    query = query.order_by(Posts.date_created.desc())
    offset = (page - 1) * limit
    posts = await db_ops.read_query(query=query, limit=limit, offset=offset)
    logger.debug(f"notes returned from pagination query {posts}")
    if isinstance(posts, str):
        logger.error(f"Unexpected result from read_query: {posts}")
        posts = []
    else:
        posts = [post.to_dict() for post in posts]
    # offset date_created and date_updated to user's timezone
    for post in posts:
        post["date_created"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=post["date_created"],
            friendly_string=True,
        )
        post["date_updated"] = await date_functions.timezone_update(
            user_timezone=user_timezone,
            date_time=post["date_updated"],
            friendly_string=True,
        )
    found = len(posts)
    posts_count = await db_ops.count_query(query=query)

    current_count = found

    total_pages = -(-posts_count // limit)  # Ceiling division
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
    logger.info(f"Found {found} posts")
    return templates.TemplateResponse(
        request=request,
        name="/posts/pagination.html",
        context={
            "posts": posts,
            "found": found,
            "posts_count": posts_count,
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
