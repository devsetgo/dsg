# -*- coding: utf-8 -*-
from datetime import datetime

# from pytz import timezone, UTC
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select, Text, and_, asc, cast, or_

from ..db_tables import InterestingThings,Categories
from ..functions import date_functions
from ..functions import ai
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
    context = {"page":"things","request": request, "things": things}
    return templates.TemplateResponse(
        request=request, name="/interesting-things/index.html", context=context
    )

@router.get("/categories", response_class=JSONResponse)
async def get_categories():
    categories = await db_ops.read_query(
        Select(Categories).where(Categories.is_thing==True).order_by(asc(Categories.name))
    )
    cat_list = [cat.to_dict()["name"] for cat in categories]
    return cat_list

@router.get("/pagination")
async def read_things_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    category: str = Query(None, description="Category"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(20, description="Number of interesting things per page"),
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
    offset = (page - 1) * limit
    query = (
        query.order_by(InterestingThings.date_created.desc())
        .limit(limit)
        .offset(offset)
    )
    things = await db_ops.read_query(query=query)
    logger.debug(f"interesting things returned from pagination query {things}")
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
        f"/interesting-things/pagination?page={page - 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page > 1
        else None
    )
    next_page_url = (
        f"/interesting-things/pagination?page={page + 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page < total_pages
        else None
    )
    logger.info(f"Found {found} interesting things")
    return templates.TemplateResponse(
        request=request,
        name="/interesting-things/pagination.html",
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


@router.get("/new")
async def new_thing(request: Request):
    return templates.TemplateResponse(
        request=request, name="/interesting-things/new.html", context={"request": request}
    )

@router.post("/new")
async def create_thing(
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
    thing = InterestingThings(
        title=title,
        summary=summary,
        user_id=user_identifier,
        category=category,
    )
    data = await db_ops.create_one(thing)
    if isinstance(data, dict):
        logger.error(f"Error creating thing: {data}")
        return RedirectResponse(url="/error/418", status_code=302)

    logger.debug(f"Created interesting-things: {thing}")
    logger.info(f"Created interesting-things with ID: {data.pkid}")

    return RedirectResponse(url=f"/interesting-thing/view/{data.pkid}", status_code=302)



# @router.get("/edit/{post_id}")
# async def edit_post_form(
#     request: Request,
#     post_id: str = Path(...),
#     user_info: dict = Depends(check_login),
# ):
#     user_identifier = user_info["user_identifier"]
#     user_timezone = user_info["timezone"]

#     query = Select(Posts).where(
#         and_(Posts.user_id == user_identifier, Posts.pkid == post_id)
#     )
#     post = await db_ops.read_one_record(query=query)
#     if post is None:
#         logger.warning(f"No post found with ID: {post_id} for user: {user_identifier}")
#         return RedirectResponse(url="/posts", status_code=302)

#     post = post.to_dict()

#     # offset date_created and date_updated to user's timezone
#     post["date_created"] = await date_functions.timezone_update(
#         user_timezone=user_timezone,
#         date_time=post["date_created"],
#         friendly_string=True,
#     )
#     post["date_updated"] = await date_functions.timezone_update(
#         user_timezone=user_timezone,
#         date_time=post["date_updated"],
#         friendly_string=True,
#     )

#     logger.info(
#         f"Returning edit form for post with ID: {post_id} for user: {user_identifier}"
#     )

#     return templates.TemplateResponse(
#         request=request,
#         name="/posts/edit.html",
#         context={"post": post},  # , "summary": ai.mood_analysis},
#     )


# @router.post("/edit/{post_id}")
# async def update_post(
#     background_tasks: BackgroundTasks,
#     request: Request,
#     post_id: str = Path(...),
#     user_info: dict = Depends(check_login),
# ):
#     user_info["user_identifier"]
#     user_info["timezone"]

#     # Fetch the old data
#     old_data = await db_ops.read_one_record(
#         query=Select(Posts).where(Posts.pkid == post_id)
#     )
#     old_data = old_data.to_dict()

#     # Get the new data from the form
#     form = await request.form()

#     # Initialize the updated data dictionary with the current date and time
#     updated_data = {"date_updated": datetime.utcnow()}

#     # List of fields to update
#     fields = ["mood", "post", "tags", "summary", "mood_analysis"]
#     # Compare the old data to the new data
#     for field in fields:
#         new_value = form.get(field)
#         if new_value is not None and new_value != old_data.get(field):
#             if field == "tags":
#                 # Ensure tags is a list
#                 if isinstance(new_value, str):
#                     new_value = [tag.strip() for tag in new_value.split(",")]
#                 elif not isinstance(new_value, list):
#                     new_value = [new_value]
#             updated_data[field] = new_value

#     # Update the database
#     data = await db_ops.update_one(
#         table=Posts, record_id=post_id, new_values=updated_data
#     )
#     logger.info(f"Updated post with ID: {post_id}")
#     # background_tasks.add_task(
#     #     notes_metrics.update_notes_metrics, user_id=user_identifier
#     # )
#     return RedirectResponse(url=f"/posts/view/{data.pkid}", status_code=302)

# get /item/{id}

# post (edit) /item/{id}

# post (delete) /delete/{id}

#
