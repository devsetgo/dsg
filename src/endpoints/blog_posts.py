# -*- coding: utf-8 -*-
"""
This module is responsible for managing blog posts within the web application. It includes functionalities for creating, retrieving, updating, and deleting blog posts. The module interacts with the application's database to perform these operations, ensuring data persistence and integrity.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - SQLAlchemy: Used for database interactions.
    - FastAPI: Provides the web framework for routing and handling HTTP requests.

Functions:
    - create_post(title, content): Creates a new blog post with the given title and content.
    - get_posts(): Retrieves all blog posts from the database.
    - get_post(post_id): Retrieves a single blog post by its ID.
    - update_post(post_id, title, content): Updates the title and content of an existing blog post.
    - delete_post(post_id): Deletes a blog post by its ID.

Usage:
    This module is intended to be imported and used by other parts of the application, particularly where blog post management functionality is required. It provides a clear API for interacting with blog post data.
"""
from datetime import datetime

# from pytz import timezone, UTC
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select, Text, and_, asc, cast, or_

from ..db_tables import Categories, Posts, Users
from ..functions import ai, date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()


async def get_user_name(user_id: str):
    query = Select(Users).where(Users.pkid == user_id)
    user = await db_ops.read_one_record(query=query)
    user = user.to_dict()
    full_name = f"{user['first_name']} {user['last_name']}"
    return full_name


@router.get("/")
async def list_of_posts(
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(10, description="Limit for pagination"),
    tag: str = Query(None, description="Tag search"),
    category: str = Query(None, description="Category to search by"),
    # user_info: dict = Depends(check_login),
):
    context = {"page": "posts", "request": request}
    return templates.TemplateResponse(
        request=request, name="/posts/index.html", context=context
    )


@router.get("/categories", response_class=JSONResponse)
async def get_categories():
    categories = await db_ops.read_query(
        Select(Categories)
        .where(Categories.is_post == True)
        .order_by(asc(Categories.name))
    )
    try:
        cat_list = [cat.to_dict()["name"] for cat in categories]
        return cat_list
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []


@router.get("/delete/{post_id}")
async def delete_post_form(
    request: Request,
    post_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    query = Select(Posts).where(
        and_(Posts.user_id == user_identifier, Posts.pkid == post_id)
    )
    post = await db_ops.read_one_record(query=query)

    return templates.TemplateResponse(
        request=request, name="/posts/delete.html", context={"post": post}
    )


@router.post("/delete/{post_id}")
async def delete_note(
    request: Request,
    post_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    query = Select(Posts).where(
        and_(Posts.user_id == user_identifier, Posts.pkid == post_id)
    )
    post = await db_ops.read_one_record(query=query)

    if post is None:
        logger.warning(f"No post found with ID: {post_id} for user: {user_identifier}")
        return RedirectResponse(url="/posts", status_code=302)

    await db_ops.delete_one(table=Posts, record_id=post_id)

    logger.info(f"Deleted post with ID: {post_id}")
    # background_tasks.add_task(
    #     notes_metrics.update_notes_metrics, user_id=user_identifier
    # )
    return RedirectResponse(url="/posts", status_code=302)


@router.get("/edit/{post_id}")
async def edit_post_form(
    request: Request,
    post_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    query = Select(Posts).where(
        and_(Posts.user_id == user_identifier, Posts.pkid == post_id)
    )
    post = await db_ops.read_one_record(query=query)
    if post is None:
        logger.warning(f"No post found with ID: {post_id} for user: {user_identifier}")
        return RedirectResponse(url="/posts", status_code=302)

    post = post.to_dict()

    # offset date_created and date_updated to user's timezone
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

    logger.info(
        f"Returning edit form for post with ID: {post_id} for user: {user_identifier}"
    )

    return templates.TemplateResponse(
        request=request,
        name="/posts/edit.html",
        context={"post": post},  # , "summary": ai.mood_analysis},
    )


@router.post("/edit/{post_id}")
async def update_post(
    background_tasks: BackgroundTasks,
    request: Request,
    post_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]
    user_info["timezone"]

    # Fetch the old data
    old_data = await db_ops.read_one_record(
        query=Select(Posts).where(Posts.pkid == post_id)
    )
    old_data = old_data.to_dict()

    # Get the new data from the form
    form = await request.form()

    # Initialize the updated data dictionary with the current date and time
    updated_data = {"date_updated": datetime.utcnow()}

    # List of fields to update
    fields = ["mood", "post", "tags", "summary", "mood_analysis"]
    # Compare the old data to the new data
    for field in fields:
        new_value = form.get(field)
        if new_value is not None and new_value != old_data.get(field):
            if field == "tags":
                # Ensure tags is a list
                if isinstance(new_value, str):
                    new_value = [tag.strip() for tag in new_value.split(",")]
                elif not isinstance(new_value, list):
                    new_value = [new_value]
            updated_data[field] = new_value

    # Update the database
    data = await db_ops.update_one(
        table=Posts, record_id=post_id, new_values=updated_data
    )
    logger.info(f"Updated post with ID: {post_id}")
    # background_tasks.add_task(
    #     notes_metrics.update_notes_metrics, user_id=user_identifier
    # )
    return RedirectResponse(url=f"/posts/view/{data.pkid}", status_code=302)


@router.get("/new")
async def new_post_form(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]

    # query = Select(Users).where(Users.pkid == user_identifier)
    # user = await db_ops.read_one_record(query=query)
    # if user is None:
    #     logger.error(f"User not found with ID: {user_identifier}")
    #     HTTPException(status_code=401, detail="Unauthorized")

    return templates.TemplateResponse(
        request=request, name="posts/new.html", context={}
    )


@router.post("/new")
async def create_post(
    background_tasks: BackgroundTasks,
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]

    form = await request.form()
    category = form["category"]
    content = form["content"]
    title = form["title"]

    logger.debug(f"Received category: {category} and content: {content}")

    # Get the tags and summary from OpenAI
    analysis = await ai.get_tags(content=content)
    summary = await ai.get_summary(content=content, sentence_length=3)
    logger.info(f"Received analysis from AI: {analysis}")
    # Create the post
    post = Posts(
        title=title,
        summary=summary,
        content=content,
        user_id=user_identifier,
        category=category,
        tags=analysis["tags"],
    )
    data = await db_ops.create_one(post)
    if isinstance(data, dict):
        logger.error(f"Error creating post: {data}")
        return RedirectResponse(url="/error/418", status_code=302)

    logger.debug(f"Created Post: {post}")
    logger.info(f"Created post with ID: {data.pkid}")

    return RedirectResponse(url=f"/posts/view/{data.pkid}", status_code=302)


@router.get("/pagination")
async def read_posts_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    category: str = Query(None, description="Category"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(5, description="Number of posts per page"),
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
    query = Select(Posts).where(
        or_(
            Posts.summary.contains(search_term) if search_term else True,
            (Posts.title.contains(search_term) if search_term else True),
        )
    )

    # filter by date range
    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(
            (Posts.date_created >= start_date) & (Posts.date_created <= end_date)
        )
    if category:
        query = query.where(Posts.category == category)
    # order and limit the results
    offset = (page - 1) * limit
    query = query.order_by(Posts.date_created.desc()).limit(limit).offset(offset)
    posts = await db_ops.read_query(query=query)
    logger.debug(f"posts returned from pagination query {posts}")
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
    count_query = Select(Posts)
    posts_count = await db_ops.count_query(query=count_query)

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
    context = {
        "page": "posts",
        "posts": posts,
        "found": found,
        "posts_count": posts_count,
        "total_pages": total_pages,
        "start_count": offset + 1,
        "current_count": offset + current_count,
        "current_page": page,
        "prev_page_url": prev_page_url,
        "next_page_url": next_page_url,
    }
    return templates.TemplateResponse(
        request=request,
        name="/posts/pagination.html",
        context=context,
    )

# get /item/{id}
@router.get("/view/{post_id}")
async def get_post_id(request: Request, post_id: str):
    user_timezone = request.session.get("timezone", None)
    if user_timezone is None:
        user_timezone = "America/New_York"

    query = Select(Posts).where(Posts.pkid == post_id)
    post = await db_ops.read_one_record(query=query)

    if post is None:
        logger.warning(f"No post found with ID: {post_id}")
        return RedirectResponse(url="/error/404", status_code=303)

    post = post.to_dict()

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
    post["full_name"] = await get_user_name(user_id=post["user_id"])
    context = {"request": request, "post": post}
    return templates.TemplateResponse(
        request=request, name="/posts/view.html", context=context
    )
