# -*- coding: utf-8 -*-
"""
This module defines the administrative functionalities for the web application, including the admin dashboard view and user management.

It utilizes FastAPI for routing and depends on various internal modules such as `dsg_lib` for common functions like email validation, `db_tables` for database models, and `functions` for specific operations like password hashing and login checks. The module also uses `loguru` for logging and `sqlalchemy` for database operations.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - FastAPI: For creating API routes.
    - loguru: For logging.
    - sqlalchemy: For database operations.
    - dsg_lib: A custom library for common functions like email validation.
    - db_tables: Defines the SQLAlchemy database models used in the application.
    - functions: Contains utility functions for date manipulation, note import, password hashing, and login checks.
    - resources: Includes database operations and template rendering utilities.

Routes:
    - GET "/": Displays the admin dashboard. Requires login verification.
    - GET "/user/{user_id}": Fetches and displays details for a specific user by their ID. Requires login verification.
    - POST "/user/{update_user_id}": Updates details for a specific user by their ID. Requires login verification.
    - POST "/user/access/{update_user_id}": Modifies user access roles for a specific user by their ID. Requires admin access.
    - GET "/failed-login-attempts": Lists all failed login attempts. Useful for monitoring unauthorized access attempts. Requires login verification.
    - GET "/note-ai-check": Lists notes pending AI review. Allows admins to manually trigger AI checks on notes. Requires login verification.
    - GET "/note-ai-check/{user_id}": Triggers AI processing for all notes associated with a specific user. Designed to facilitate batch processing of user notes. Requires login verification.
"""
import secrets
from collections import defaultdict
from datetime import datetime

from dsg_lib.common_functions.email_validation import validate_email_address
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    Response,
)
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select, and_

# , FailedLoginAttempts,JobApplications
from ..db_tables import Categories, Notes, Posts, Users, WebLinks
from ..functions import date_functions, link_preview, note_import
from ..functions.hash_function import check_password_complexity, hash_password
from ..functions.login_required import check_login
from ..functions.models import RoleEnum
from ..resources import db_ops, templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    user_info["is_admin"]

    user_list = await get_list_of_users(user_timezone=user_timezone)

    context = {"page": "admin", "user_identifier": user_identifier, "users": user_list}
    return templates.TemplateResponse(
        request=request, name="/admin/dashboard.html", context=context
    )


async def get_list_of_users(user_timezone: str):
    try:
        query = Select(Users)
        users = await db_ops.read_query(query=query)
        users = [user.to_dict() for user in users]

        for user in users:
            for k, _v in user.items():
                if k.startswith("date_"):
                    user[k] = await date_functions.timezone_update(
                        user_timezone=user_timezone,
                        date_time=user[k],
                        friendly_string=True,
                    )
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        users = []
    return users


@router.get("/categories", response_class=HTMLResponse)
async def admin_categories(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    context = {"page": "admin", "user_identifier": user_identifier}
    logger.debug(f"categories: {context}")
    return templates.TemplateResponse(
        request=request, name="/admin/categories.html", context=context
    )


@router.get("/categories-table", response_class=HTMLResponse)
async def admin_categories_table(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    query = Select(Categories)
    categories = await db_ops.read_query(query=query)
    categories = [category.to_dict() for category in categories]

    # Get a count of posts for each category
    post_query = Select(Posts)
    post_count = await db_ops.read_query(query=post_query)
    it_query = Select(WebLinks)
    it_count = await db_ops.read_query(query=it_query)

    category_count = defaultdict(int)

    if isinstance(post_count, list):
        for post in post_count:
            if hasattr(post, "to_dict"):
                post = post.to_dict()
                category_count[post["category"].lower()] += 1
            else:
                logger.error(f"Unexpected type in post_count: {type(post)}")
    else:
        logger.error(f"post_count is not a list: {post_count}")

    if isinstance(it_count, list):
        for it in it_count:
            if hasattr(it, "to_dict"):
                it = it.to_dict()
                category_count[it["category"].lower()] += 1
            else:
                logger.error(f"Unexpected type in it_count: {type(it)}")
    else:
        logger.error(f"it_count is not a list: {it_count}")

    category_count_list = [
        {"category": category, "count": count}
        for category, count in category_count.items()
    ]
    logger.debug(category_count_list)
    context = {"categories": categories, "category_count_list": category_count_list}
    logger.debug(f"categories-table: {context}")
    return templates.TemplateResponse(
        request=request, name="/admin/categories-table.html", context=context
    )


@router.get("/category-edit", response_class=HTMLResponse)
async def admin_category_edit(
    request: Request, category_id: str = None, user_info: dict = Depends(check_login)
):
    context = {"categories": None, "rand": secrets.token_urlsafe(2)}
    if category_id is not None:
        query = Select(Categories).where(Categories.pkid == category_id)
        category = await db_ops.read_one_record(query=query)
        context["category"] = category.to_dict()

    logger.debug(f"category-edit: {context}")
    return templates.TemplateResponse(
        request=request, name="/admin/category-form.html", context=context
    )


@router.post("/category-edit", response_class=HTMLResponse)
async def add_edit_category(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_info["timezone"]
    form = await request.form()
    name = form["name"]
    description = form["description"]
    is_post = False
    is_weblink = False
    is_system = False

    if "is_post" in form and form["is_post"] == "on":
        is_post = True

    if "is_weblink" in form and form["is_weblink"] == "on":
        is_weblink = True

    if "is_system" in form and form["is_system"] == "on":
        is_system = True

    context = {"category_data": None}
    if "category_id" in form and form["category_id"] != "":
        category_id = form["category_id"]
        # Fetch the old data
        old_data = await db_ops.read_one_record(
            query=Select(Categories).where(Categories.pkid == category_id)
        )
        old_data = old_data.to_dict()

        updated_data = {
            "name": name,
            "description": description,
            "is_post": is_post,
            "is_weblink": is_weblink,
            "is_system": is_system,
            "date_updated": datetime.utcnow(),
        }

        # Update the database
        data = await db_ops.update_one(
            table=Categories, record_id=category_id, new_values=updated_data
        )
        context["category_data"] = data.to_dict()
        context["status"] = "updated"
    else:
        # Process the form data and save the category
        category_data = Categories(
            name=form["name"],
            description=form["description"],
            is_post=is_post,
            is_weblink=is_weblink,
            is_system=is_system,
        )

        data = await db_ops.create_one(category_data)
        context["category_data"] = data.to_dict()
        context["status"] = "created"

    logger.debug(f"category-edit: {context}")
    return templates.TemplateResponse(
        request=request, name="/admin/category-confirm.html", context=context
    )


@router.get("/user/{user_id}", response_class=HTMLResponse)
async def admin_user(
    request: Request,
    user_id: str,
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    user_info["is_admin"]

    query = Select(Users).where(Users.pkid == user_id)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()
    for k, _v in user.items():
        if k.startswith("date_"):
            user[k] = await date_functions.timezone_update(
                user_timezone=user_timezone,
                date_time=user[k],
                friendly_string=True,
            )

    notes_query = Select(Notes).where(Notes.user_id == user_id)
    notes_count = await db_ops.count_query(query=notes_query)

    # job_app_query = Select(JobApplications).where(JobApplications.user_id == user_id)
    # job_app_count = await db_ops.count_query(query=job_app_query)

    context = {
        "page": "admin",
        "user": user,
        "notes_count": notes_count,
        # "job_app_count": job_app_count,
        "random_pass": secrets.token_urlsafe(10),
        "roles": [
            role.value for role in sorted(RoleEnum, key=lambda x: x.name)
        ],  # List of all role values from the Enum, sorted by name
    }
    response = templates.TemplateResponse(
        request=request, name="/admin/user.html", context=context
    )

    return response


@router.post("/user/{update_user_id}", response_class=HTMLResponse)
async def admin_update_user(
    request: Request,
    update_user_id: str,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    if update_user_id == user_identifier:
        return Response(headers={"HX-Redirect": "/error/422"}, status_code=200)

    form = await request.form()

    account_action = form.get("account-action")

    if account_action == "delete":
        data = await db_ops.delete_one(table=Users, record_id=update_user_id)
        logger.info(f"User {update_user_id} deleted by {user_identifier}")
        logger.debug(f"data: {data}")
        data_notes = await db_ops.read_query(
            query=Select(Notes).where(Notes.user_id == update_user_id)
        )
        if data_notes is not None:
            logger.warning(f"No post found with ID: {update_user_id}")
            return RedirectResponse(url="/error/404", status_code=303)
        response = Response(
            headers={"HX-Redirect": "/admin/#access-tab"}, status_code=200
        )

        return response

    new_values = {}

    new_password = form.get("new-password-entry")

    is_complex = check_password_complexity(password=new_password)
    if is_complex == False:
        return Response(headers={"HX-Redirect": "/error/400"}, status_code=200)

    change_email_entry = form.get("change-email-entry")

    if account_action == "lock":
        new_values["is_locked"] = True

    elif new_password != "":
        hashed_password = hash_password(new_password)
        new_values["password"] = hashed_password

    elif change_email_entry != "":
        valid_email = validate_email_address(
            change_email_entry, check_deliverability=True
        )
        if valid_email["valid"]:
            new_values["email"] = change_email_entry
        else:
            return Response(headers={"HX-Redirect": "/error/400"}, status_code=200)

    data = await db_ops.update_one(
        table=Users, record_id=update_user_id, new_values=new_values
    )

    query = Select(Users).where(Users.pkid == update_user_id)
    user = await db_ops.read_one_record(query=query)

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user = user.to_dict()

    response = Response(
        headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
    )

    return response


@router.post("/user/access/{update_user_id}", response_class=HTMLResponse)
async def admin_update_user_access(
    request: Request,
    update_user_id: str,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    is_admin = user_info["is_admin"]

    logger.debug(f"User {user_identifier} is admin: {is_admin}")

    if is_admin:
        form = await request.form()
        new_data = {}
        for key, value in form.items():
            role = key
            new_data[role] = value == "true"

        logger.debug(f"Form data: {new_data}")

        new_values = {
            "roles": new_data,
            "update_by": user_identifier,
            "date_updated": datetime.utcnow(),
        }

        logger.debug(f"Updating database with values: {new_values}")
        data = await db_ops.update_one(
            table=Users, record_id=update_user_id, new_values=new_values
        )
        logger.debug(f"Database update result: {data}")

        response = Response(
            headers={"HX-Redirect": f"/admin/user/{update_user_id}"}, status_code=200
        )

        return response
    else:
        return Response(headers={"HX-Redirect": "/error/403"}, status_code=200)


@router.get("/note-ai-check", response_class=HTMLResponse)
async def admin_note_ai_check(
    request: Request,
    user_info: dict = Depends(check_login),
):
    """
    Handles the GET request for the "/note-ai-check" route.

    Args:
        request (Request): The incoming request.
        user_info (dict): The user information, obtained from the check_login dependency.

    Returns:
        TemplateResponse: The response, rendered using a template.
    """

    # Log the start of the process
    logger.info("Processing note AI check for admin")

    # Extract user identifier from user_info
    user_identifier = user_info["user_identifier"]

    # These lines don't seem to do anything. Consider removing them or using the values.
    user_info["timezone"]
    user_info["is_admin"]

    # Log the user identifier
    logger.debug(f"User identifier: {user_identifier}")

    # Create a query to select notes that need AI check
    notes_query = Select(Notes).where(Notes.ai_fix == True)

    # Execute the query and get the results
    notes = await db_ops.read_query(query=notes_query)
    notes = [note.to_dict() for note in notes]

    # Create a query to select weblinks that need AI check
    weblinks_query = Select(WebLinks).where(WebLinks.ai_fix == True)

    # Execute the query and get the results
    weblinks = await db_ops.read_query(query=weblinks_query)
    weblinks = [weblink.to_dict() for weblink in weblinks]

    # Log the number of retrieved notes and weblinks
    user_note_count = []
    for note in notes:
        user_id = note["user_id"]
        note_date = note["date_created"]
        found = False
        for user in user_note_count:
            if user["user_id"] == user_id:
                user["count"] += 1
                if note_date > user["last_note_date"]:
                    user["last_note_date"] = note_date
                found = True
                break
        if not found:
            user_note_count.append(
                {
                    "user_id": user_id,
                    "user_name": None,
                    "count": 1,
                    "last_note_date": note_date,
                    "weblinks_ai_fix_count": 0,  # Initialize weblinks count
                }
            )

    # Query to get the weblinks with ai_fix set to True
    weblinks_query = Select(WebLinks).where(WebLinks.ai_fix == True)
    weblinks = await db_ops.read_query(query=weblinks_query)
    weblinks = [weblink.to_dict() for weblink in weblinks]

    # Update user_note_count with weblinks count
    for weblink in weblinks:
        user_id = weblink["user_id"]
        for user in user_note_count:
            if user["user_id"] == user_id:
                user["weblinks_ai_fix_count"] += 1
                break

    for user in user_note_count:
        user_id = user["user_id"]
        query = Select(Users).where(Users.pkid == user_id)
        user_data = await db_ops.read_one_record(query=query)
        user_data = user_data.to_dict()
        user["user_name"] = user_data["user_name"]

    # Log the number of retrieved notes and weblinks
    logger.debug(f"Retrieved {len(notes)} notes for AI check")
    logger.debug(f"Retrieved {len(weblinks)} weblinks for AI check")

    # Create the context for the template
    context = {
        "page": "admin",
        "user_identifier": user_identifier,
        "notes": notes,
        "weblinks": weblinks,
        "user_note_count": user_note_count,
    }

    # Log the end of the process
    logger.info("Finished processing note AI check for admin")

    # Render the template and return the response
    return templates.TemplateResponse(
        request=request, name="/admin/note_ai_check.html", context=context
    )


@router.get("/note-ai-check/{user_id}")
async def admin_note_ai_check_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    user_info: dict = Depends(check_login),
):
    # Create a query to select notes that need AI check
    query = Select(Notes).where(and_(Notes.user_id == user_id, Notes.ai_fix == True))

    # Execute the query and get the results
    notes = await db_ops.read_query(query=query)
    if isinstance(notes, dict):
        logger.error(f"Error fetching notes: {notes}")
        raise HTTPException(status_code=404, detail="No notes found for user")
    notes = [note.to_dict() for note in notes]
    list_of_ids: list = []
    for note in notes:
        list_of_ids.append(note["pkid"])

    # print(list_of_ids)
    background_tasks.add_task(
        note_import.process_ai, user_identifier=user_id, list_of_ids=list_of_ids
    )
    return RedirectResponse(url="/admin", status_code=302)


# weblink-fix for user
@router.get("/weblink-fix/{user_id}")
async def admin_weblink_fix_user(
    user_id: str,
    background_tasks: BackgroundTasks,
    user_info: dict = Depends(check_login),
):
    query = Select(WebLinks).where(
        and_(WebLinks.user_id == user_id, WebLinks.ai_fix == True)
    )

    # Execute the query and get the results
    links = await db_ops.read_query(query=query)
    links = [link.to_dict() for link in links]
    list_of_ids: list = []
    for link in links:
        list_of_ids.append(link["pkid"])

    background_tasks.add_task(
        link_preview.update_weblinks_ai,
        list_of_ids=list_of_ids,
    )
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/export-notes", response_class=HTMLResponse)
async def export_notes(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    user_info["is_admin"]

    # Fetch all notes from the database with user_name
    query = Select(Notes).join(Users, Notes.user_id == Users.pkid)
    result = await db_ops.read_query(query=query)
    notes = [note.to_dict() for note in result]
    # Render the template with the data
    context = {
        "page": "admin",
        "user_identifier": user_identifier,
        "notes": notes,
    }

    return templates.TemplateResponse(
        request=request, name="/admin/export-notes.html", context=context
    )
