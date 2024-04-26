# -*- coding: utf-8 -*-
import csv
import io
import re
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
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pytz import timezone
from sqlalchemy import Select, Text, and_, between, cast, extract, or_, text

from ..db_tables import Notes
from ..functions import ai, date_functions, note_import, notes_metrics
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()


@router.get("/")
async def read_notes(
    request: Request,
    offset: int = Query(0, description="Offset for pagination"),
    limit: int = Query(100, description="Limit for pagination"),
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    metrics = await notes_metrics.get_metrics(
        user_identifier=user_identifier, user_timezone=user_timezone
    )

    context = {"user_identifier": user_identifier, "metrics": metrics}
    return templates.TemplateResponse(
        request=request, name="/notes/dashboard.html", context=context
    )


@router.get("/issues")
async def get_note_issue(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    if user_identifier is None:
        logger.debug("User identifier is None, redirecting to login")
        return RedirectResponse(url="/users/login", status_code=302)

    pattern = re.compile("[^a-zA-Z, ]")

    if settings.db_driver.startswith("sqlite"):
        # Fetch all notes from the SQLite database
        query = Select(Notes).where(Notes.user_id == user_identifier)
        all_notes = await db_ops.read_query(query=query)
        # Filter the notes in Python using the regular expression
        notes = []
        for note in all_notes:
            if any(pattern.search(tag) for tag in note.tags):
                notes.append(note)
                if len(notes) == 5:
                    break
    elif settings.db_driver.startswith("postgres"):
        # Use the regular expression in the PostgreSQL query
        query = Select(Notes).where(
            text(
                f"EXISTS (SELECT 1 FROM json_array_elements_text(tags) as tag WHERE tag ~* '{pattern.pattern}')"
            )
        )
        query = query.where(Notes.user_id == user_identifier)
        notes = await db_ops.read_query(query=query, limit=5)
    else:
        raise ValueError("Untested database driver")

    # offset date_created and date_updated to user's timezone
    notes = [note.to_dict() for note in notes]
    metrics = {"word_count": 0, "note_count": len(notes), "character_count": 0}
    for note in notes:

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
        metrics["word_count"] += len(note["note"].split())
        metrics["character_count"] += len(note["note"])
    logger.info(f"Found {len(notes)} notes for user {user_identifier}")

    return templates.TemplateResponse(
        request=request,
        name="/notes/issues.html",
        context={"notes": notes, "metrics": metrics},
    )


@router.get("/ai-resubmit/{note_id}")
async def ai_update_note(
    request: Request, note_id: str, user_info: dict = Depends(check_login)
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    if note is None:
        logger.warning(f"No note found with ID: {note_id} for user: {user_identifier}")
        return RedirectResponse(url="/error/404", status_code=404)

    note = note.to_dict()

    return templates.TemplateResponse(
        request=request, name="/notes/ai-resubmit.html", context={"note": note}
    )


@router.get("/ai-fix/{note_id}")
async def ai_fix_processing(
    request: Request, note_id: str, user_info: dict = Depends(check_login)
):
    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)
    note = note.to_dict()

    # Get the tags and summary from OpenAI
    analysis = await ai.get_analysis(content=note["note"])

    logger.info(f"Received analysis from AI: {analysis}")
    # Create the note
    note_update = {
        "tags": analysis["tags"]["tags"],
        "summary": analysis["summary"],
        "mood_analysis": analysis["mood_analysis"],
    }

    data = await db_ops.update_one(
        table=Notes, record_id=note["pkid"], new_values=note_update
    )
    data = data.to_dict()
    logger.info(f"Resubmited note to AI with ID: {data['pkid']}")
    return RedirectResponse(url=f"/notes/view/{data['pkid']}?ai=true", status_code=302)


@router.get("/bulk")
async def bulk_note_form(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
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
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

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
    csrf_protect: CsrfProtect = Depends(),
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
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]

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

    return RedirectResponse(url=f"/notes/view/{data.pkid}", status_code=302)


@router.get("/delete/{note_id}")
async def delete_note_form(
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

    return templates.TemplateResponse(
        request=request, name="/notes/delete.html", context={"note": note}
    )


@router.post("/delete/{note_id}")
async def delete_note(
    request: Request,
    note_id: str = Path(...),
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
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

    await db_ops.delete_one(table=Notes, record_id=note_id)

    logger.info(f"Deleted note with ID: {note_id}")

    return RedirectResponse(url="/notes", status_code=302)


@router.get("/new")
async def new_note_form(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    # demo_note = get_note_demo_paragraph()
    # logger.info("Generated demo note")
    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={}
    )


@router.post("/new")
async def create_note(
    request: Request,
    user_info: dict = Depends(check_login),
    csrf_protect: CsrfProtect = Depends(),
):

    user_identifier = user_info["user_identifier"]
    user_timezone = user_info["timezone"]
    form = await request.form()
    mood = form["mood"]
    note = form["note"]

    logger.debug(f"Received mood: {mood} and note: {note}")

    # Get the tags and summary from OpenAI
    analysis = await ai.get_analysis(content=note)

    logger.info(f"Received analysis from AI: {analysis}")
    # Create the note
    note = Notes(
        mood=mood,
        note=note,
        tags=analysis["tags"]["tags"],
        summary=analysis["summary"],
        mood_analysis=analysis["mood_analysis"],
        user_id=user_identifier,
    )
    data = await db_ops.create_one(note)

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
    # csrf_protect: CsrfProtect = Depends(),
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
    # user_identifier = request.session.get("user_identifier")
    # user_timezone = request.session.get("timezone")

    logger.critical(
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
    query = query.order_by(Notes.date_created.desc())
    offset = (page - 1) * limit
    notes = await db_ops.read_query(query=query, limit=limit, offset=offset)
    logger.debug(f"notes returned from pagination query {notes}")
    if isinstance(notes, str):
        logger.error(f"Unexpected result from read_query: {notes}")
        notes = []
    else:
        notes = [note.to_dict() for note in notes]
    # offset date_created and date_updated to user's timezone
    for note in notes:
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
    found = len(notes)
    note_count = await db_ops.count_query(query=query)
    # if offset == 0:
    current_count = found
    # else:
    #     current_count = note_count

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
            "current_count": current_count,
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
    csrf_protect: CsrfProtect = Depends(),
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

    # get notes within 7 days of today
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
    for note in notes:
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
        metrics["word_count"] += len(note["note"].split())
        metrics["character_count"] += len(note["note"])
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
        context={"notes": notes, "metrics": metrics, "today": formatted_today},
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
