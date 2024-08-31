# -*- coding: utf-8 -*-
"""
This module, `notes.py`, is designed for handling note-taking functionalities within a web application. It provides the capability to create, read, update, and delete notes. Additionally, it supports importing notes from CSV files and offers time-based features, such as setting reminders for notes. The module leverages FastAPI for creating API endpoints and utilizes Python's built-in `datetime` module for time-related operations.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - fastapi: For creating API routes and handling HTTP requests.
    - csv: For parsing CSV files during note import operations.
    - io: For handling in-memory file operations, useful in parsing CSV content.
    - datetime: For managing dates and times, including support for time zones and time deltas.

Features:
    - CRUD operations for notes.
    - Importing notes from CSV files.
    - Setting reminders and deadlines for notes.

Usage:
    This module is intended to be used as part of a larger FastAPI application. It can be mounted as a router to handle note-related routes, providing a RESTful API for managing notes.

Routes:
    - GET /: Retrieves a list of notes for the user.
    - GET /metrics/counts: Retrieves metrics related to the user's notes.
    - GET /ai-resubmit/{note_id}: Displays a form to resubmit a note for AI processing.
    - GET /ai-fix/{note_id}: Initiates AI processing to fix a note's content.
    - GET /bulk: Displays a form for bulk note import.
    - POST /bulk: Handles bulk note import from a CSV file.
    - GET /edit/{note_id}: Displays a form to edit a note.
    - POST /edit/{note_id}: Updates a note with new content.
    - GET /delete/{note_id}: Displays a form to delete a note.
    - POST /delete/{note_id}: Deletes a note.
    - GET /issues: Retrieves notes with AI issues.
    - GET /new: Displays a form to create a new note.
    - POST /new: Creates a new note.
    - GET /pagination: Retrieves paginated notes based on search criteria.
    - GET /today: Retrieves notes for today's date.
    - GET /view/{note_id}: Displays a single note.
"""
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
from fastapi.responses import RedirectResponse
from loguru import logger
from pytz import timezone
from sqlalchemy import Select, Text, and_, between, cast, extract, or_

from ..db_tables import NoteMetrics, Notes
from ..functions import ai, date_functions, note_import, notes_metrics
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


@router.get("/")
async def read_notes(
    background_tasks: BackgroundTasks,
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(100, description="Limit for pagination"),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    note_metrics = await db_ops.read_one_record(
        query=Select(NoteMetrics).where(NoteMetrics.user_id == user_identifier)
    )

    if note_metrics is None:
        await notes_metrics.update_notes_metrics(user_id=user_identifier)
        note_metrics = await db_ops.read_one_record(
            query=Select(NoteMetrics).where(NoteMetrics.user_id == user_identifier)
        )

    metrics = None

    if note_metrics is not None:
        note_metrics = note_metrics.to_dict()
        # note_metrics.pop("pkid")
        # note_metrics.pop("date_created")
        # # note_metrics.pop("date_updated")
        # note_metrics.pop("user_id")
        metrics = note_metrics["metrics"]

        # Get the current time in UTC
        now = datetime.utcnow()

        # Calculate the time one hour ago
        one_hour_ago = now - timedelta(hours=1)

        # Get date_updated from note_metrics
        date_update = note_metrics["date_updated"]

        # Check if date_update is older than one hour
        if date_update < one_hour_ago:
            background_tasks.add_task(
                notes_metrics.update_notes_metrics, user_id=user_identifier
            )
    logger.info(f"User {user_identifier} dashboard retrieved")
    context = {
        "page": "notes",
        "user_identifier": user_identifier,
        "metrics": metrics,
        "note_metrics": note_metrics,
    }
    return templates.TemplateResponse(
        request=request, name="/notes/dashboard.html", context=context
    )


@router.get("/metrics/counts")
async def get_note_counts(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    note_metrics = await db_ops.read_one_record(
        query=Select(NoteMetrics).where(NoteMetrics.user_id == user_identifier)
    )
    if note_metrics is None:
        await notes_metrics.update_notes_metrics(user_id=user_identifier)
        note_metrics = await db_ops.read_one_record(
            query=Select(NoteMetrics).where(NoteMetrics.user_id == user_identifier)
        )

    note_metrics = note_metrics.to_dict()
    for field in ["pkid", "date_created", "date_updated", "user_id"]:
        note_metrics.pop(field, None)

    logger.debug(f"User {user_identifier} fetched note counts: {note_metrics}")
    logger.info(f"User {user_identifier} metrics retrieved")
    return templates.TemplateResponse(
        request=request,
        name="/notes/metrics.html",
        context={"note_metrics": note_metrics},
    )


@router.get("/ai-resubmit/{note_id}")
async def ai_update_note(
    request: Request, note_id: str, user_info: dict = Depends(check_login)
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    if note is None:
        logger.warning(f"No note found with ID: {note_id} for user: {user_identifier}")
        return RedirectResponse(url="/error/404", status_code=303)

    note = note.to_dict()

    return templates.TemplateResponse(
        request=request, name="/notes/ai-resubmit.html", context={"note": note}
    )


@router.get("/ai-fix/{note_id}")
async def ai_fix_processing(
    request: Request, note_id: str, user_info: dict = Depends(check_login)
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    note = note.to_dict()

    mood = None
    if note["mood"] not in ["postive", "negative", "neutral"]:
        mood = note["mood"]
    # Get the tags and summary from OpenAI
    analysis = await ai.get_analysis(content=note["note"], mood_process=mood)

    moods_list: list = [mood[0] for mood in settings.mood_analysis_weights]

    if analysis["mood_analysis"] not in moods_list:
        pass

    logger.debug(f"Received analysis from AI: {analysis}")
    # Create the note
    note_update = {
        "tags": analysis["tags"]["tags"],
        "summary": analysis["summary"],
        "mood_analysis": analysis["mood_analysis"],
        "ai_fix": False,
    }

    # If mood is not None, add it to note_update
    if analysis["mood"] is not None:
        note_update["mood"] = analysis["mood"]["mood"]

    await db_ops.update_one(table=Notes, record_id=note["pkid"], new_values=note_update)

    logger.info(f"Resubmited note to AI with ID: {note_id}")
    return RedirectResponse(url=f"/notes/view/{note_id}?ai=true", status_code=302)


@router.get("/bulk")
async def bulk_note_form(
    request: Request,
    # user_info: dict = Depends(check_login),
):
    return templates.TemplateResponse(
        request=request, name="notes/bulk.html", context={"demo_note": None}
    )


@router.post("/bulk")
async def bulk_note(
    background_tasks: BackgroundTasks,
    request: Request,
    csv_file: UploadFile = File(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    # user_identifier =  request.session.get("user_identifier")
    user_info["timezone"]

    # read the file content
    file_content = await csv_file.read()
    file_content = file_content.decode("utf-8")
    csv_reader = csv.DictReader(io.StringIO(file_content))

    # add the task to background tasks
    background_tasks.add_task(
        note_import.read_notes_from_file, csv_file=csv_reader, user_id=user_identifier
    )
    logger.info("Added task to background tasks")

    # redirect to /notes
    return RedirectResponse(url="/notes", status_code=302)


@router.get("/edit/{note_id}")
async def edit_note_form(
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)
    if note is None:
        logger.warning(f"No note found with ID: {note_id} for user: {user_identifier}")
        return RedirectResponse(url="/notes", status_code=302)

    note = note.to_dict()

    # offset date_created and date_updated to user's timezone
    note["date_created"] = await date_functions.timezone_update(
        user_timezone=user_timezone,
        date_time=note["date_created"],
        friendly_string=True,
    )
    note["date_updated"] = await date_functions.timezone_update(
        user_timezone=user_timezone,
        date_time=note["date_updated"],
        friendly_string=True,
    )

    logger.info(
        f"Returning edit form for note with ID: {note_id} for user: {user_identifier}"
    )

    return templates.TemplateResponse(
        request=request,
        name="/notes/edit.html",
        context={"note": note, "mood_analysis": ai.mood_analysis},
    )


@router.post("/edit/{note_id}")
async def update_note(
    background_tasks: BackgroundTasks,
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    # Fetch the old data
    old_data = await db_ops.read_one_record(
        query=Select(Notes).where(Notes.pkid == note_id)
    )
    old_data = old_data.to_dict()

    # Get the new data from the form
    form = await request.form()

    # Initialize the updated data dictionary with the current date and time
    updated_data = {"date_updated": datetime.utcnow()}

    # List of fields to update
    fields = ["mood", "note", "tags", "summary", "mood_analysis"]
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
        table=Notes, record_id=note_id, new_values=updated_data
    )
    logger.info(f"Updated note with ID: {note_id}")
    background_tasks.add_task(
        notes_metrics.update_notes_metrics, user_id=user_identifier
    )
    return RedirectResponse(url=f"/notes/view/{data.pkid}", status_code=302)


@router.get("/delete/{note_id}")
async def delete_note_form(
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    return templates.TemplateResponse(
        request=request, name="/notes/delete.html", context={"note": note}
    )


@router.post("/delete/{note_id}")
async def delete_note(
    background_tasks: BackgroundTasks,
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    if note is None:
        logger.warning(f"No note found with ID: {note_id} for user: {user_identifier}")
        return RedirectResponse(url="/notes", status_code=302)

    await db_ops.delete_one(table=Notes, record_id=note_id)

    logger.info(f"Deleted note with ID: {note_id}")
    background_tasks.add_task(
        notes_metrics.update_notes_metrics, user_id=user_identifier
    )
    return RedirectResponse(url="/notes", status_code=302)


@router.get("/issues")
async def get_note_issue(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    query = (
        Select(Notes)
        .where(and_(Notes.user_id == user_identifier, Notes.ai_fix == True))
        .limit(200)
    )
    notes = await db_ops.read_query(query=query)

    # offset date_created and date_updated to user's timezone
    notes = [note.to_dict() for note in notes]
    metrics = {"word_count": 0, "note_count": len(notes), "character_count": 0}
    notes = await date_functions.update_timezone_for_dates(
        data=notes, user_timezone=user_timezone
    )

    logger.info(f"Found {len(notes)} notes for user {user_identifier}")

    return templates.TemplateResponse(
        request=request,
        name="/notes/issues.html",
        context={"notes": notes, "metrics": metrics},
    )


@router.get("/new")
async def new_note_form(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_info["user_identifier"]
    user_info["timezone"]

    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={}
    )


@router.post("/new")
async def create_note(
    background_tasks: BackgroundTasks,
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_info["timezone"]
    form = await request.form()
    mood = form["mood"]
    note = form["note"]

    logger.debug(f"Received mood: {mood} and note: {note}")
    ai_fix = False
    # Get the tags and summary from OpenAI
    analysis = await ai.get_analysis(content=note)

    moods_list: list = [mood[0] for mood in settings.mood_analysis_weights]

    if analysis["mood_analysis"] not in moods_list:
        ai_fix = True

    logger.info(f"Received analysis from AI: {analysis}")
    # Create the note
    note = Notes(
        mood=mood,
        note=note,
        tags=analysis["tags"]["tags"],
        summary=analysis["summary"],
        mood_analysis=analysis["mood_analysis"],
        user_id=user_identifier,
        ai_fix=ai_fix,
    )
    data = await db_ops.create_one(note)

    background_tasks.add_task(
        notes_metrics.update_notes_metrics, user_id=user_identifier
    )
    logger.debug("Created Note: data")
    logger.info(f"Created note with ID: {data.pkid}")

    return RedirectResponse(url=f"/notes/view/{data.pkid}", status_code=302)


@router.get("/pagination")
async def read_notes_pagination(
    request: Request,
    search_term: str = Query(None, description="Search term"),
    start_date: str = Query(None, description="Start date"),
    end_date: str = Query(None, description="End date"),
    mood: str = Query(None, description="Mood"),
    page: int = Query(1, description="Page number"),
    limit: int = Query(20, description="Number of notes per page"),
    user_info: dict = Depends(check_login),
    #
):
    query_params = {
        "search_term": search_term,
        "start_date": start_date,
        "end_date": end_date,
        "mood": mood,
        "limit": limit,
    }

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    logger.info(
        f"Searching for term: {search_term}, start_date: {start_date}, end_date: {end_date}, mood: {mood}, user: {user_identifier}"
    )
    # find search_term in columns: note, mood, tags, summary
    query = Select(Notes).where(
        (Notes.user_id == user_identifier)
        & (
            or_(
                Notes.note.contains(search_term) if search_term else True,
                Notes.summary.contains(search_term) if search_term else True,
                cast(Notes.tags, Text).contains(search_term) if search_term else True,
            )
        )
    )

    # filter by mood
    if mood:
        query = query.where(Notes.mood == mood)
    # filter by date range
    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        query = query.where(
            (Notes.date_created >= start_date) & (Notes.date_created <= end_date)
        )
    # order and limit the results
    offset = (page - 1) * limit
    query = query.order_by(Notes.date_created.desc())
    count_query = query
    query = query.limit(limit).offset(offset)
    notes = await db_ops.read_query(query=query)
    logger.debug(f"notes returned from pagination query {notes}")
    if isinstance(notes, str):
        logger.error(f"Unexpected result from read_query: {notes}")
        notes = []
    else:
        notes = [note.to_dict() for note in notes]

    # offset date_created and date_updated to user's timezone
    notes = await date_functions.update_timezone_for_dates(
        data=notes, user_timezone=user_timezone
    )
    found = len(notes)
    note_count = await db_ops.count_query(query=count_query)

    current_count = found + offset

    total_pages = -(-note_count // limit)  # Ceiling division
    # Generate the URLs for the previous and next pages
    prev_page_url = (
        f"/notes/pagination?page={page - 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page > 1
        else None
    )
    next_page_url = (
        f"/notes/pagination?page={page + 1}&"
        + "&".join(f"{k}={v}" for k, v in query_params.items() if v)
        if page < total_pages
        else None
    )

    logger.info(f"Found {found} notes for user {user_identifier}")
    return templates.TemplateResponse(
        request=request,
        name="/notes/pagination.html",
        context={
            "user_identifier": user_identifier,
            "notes": notes,
            "found": found,
            "note_count": note_count,
            "total_pages": total_pages,
            "start_count": offset + 1,
            "current_count": offset + current_count,
            "current_page": page,
            "prev_page_url": prev_page_url,
            "next_page_url": next_page_url,
        },
    )


# today in history notes list
@router.get("/today")
async def read_today_notes(
    request: Request,
    user_info: dict = Depends(check_login),
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    # get today's date
    today = datetime.now(UTC)

    # calculate the dates for 7 days before and after today
    start_date = today - timedelta(days=settings.history_range)
    end_date = today + timedelta(days=settings.history_range)

    # query = Select(Notes).where(
    #     and_(
    #         Notes.user_id == user_identifier,
    #         between(Notes.date_created, start_date, end_date),
    #     )
    # )
    query = Select(Notes).where(
        and_(
            Notes.user_id == user_identifier,
            or_(
                and_(
                    extract("month", Notes.date_created) == start_date.month,
                    between(
                        extract("day", Notes.date_created), start_date.day, end_date.day
                    ),
                ),
                and_(
                    extract("month", Notes.date_created) == end_date.month,
                    between(
                        extract("day", Notes.date_created), start_date.day, end_date.day
                    ),
                ),
            ),
        )
    )
    notes = await db_ops.read_query(query=query)

    # offset date_created and date_updated to user's timezone
    notes = [note.to_dict() for note in notes]

    metrics = {"word_count": 0, "note_count": len(notes), "character_count": 0}
    notes = await date_functions.update_timezone_for_dates(
        data=notes, user_timezone=user_timezone
    )
    logger.info(f"Found {len(notes)} notes for user {user_identifier}")

    # get the user's timezone
    user_tz = timezone(user_timezone)

    # convert the UTC datetime to the user's timezone
    today_user_tz = today.astimezone(user_tz)

    # format it as "5 April"
    formatted_today = today_user_tz.strftime("%d %B")

    return templates.TemplateResponse(
        request=request,
        name="/notes/today.html",
        context={
            "notes": notes,
            "metrics": metrics,
            "today": formatted_today,
            "range": settings.history_range,
        },
    )


@router.get("/view/{note_id}")
async def read_note(
    request: Request,
    note_id: str,
    user_info: dict = Depends(check_login),
    ai: bool = None,
):
    if ai is None:
        ai = False

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    if note is None:
        logger.warning(f"No note found with ID: {note_id} for user: {user_identifier}")
        return RedirectResponse(url="/notes", status_code=302)

    note = note.to_dict()
    # offset date_created and date_updated to user's timezone
    note["date_created"] = await date_functions.timezone_update(
        user_timezone=user_timezone,
        date_time=note["date_created"],
        friendly_string=True,
    )
    note["date_updated"] = await date_functions.timezone_update(
        user_timezone=user_timezone,
        date_time=note["date_updated"],
        friendly_string=True,
    )

    logger.info(f"Returning note with ID: {note_id} for user: {user_identifier}")

    return templates.TemplateResponse(
        request=request, name="/notes/view.html", context={"note": note, "ai": ai}
    )
