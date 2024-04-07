# -*- coding: utf-8 -*-
import csv
import io
from datetime import datetime

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, or_

from ..db_tables import Notes
from ..functions import ai, date_functions, note_import, notes_metrics
from ..functions.demo_functions import get_note_demo_paragraph
from ..functions.user_check import get_user_info
from ..resources import db_ops, templates

router = APIRouter()


@router.get("/")
async def read_notes(
    request: Request,
    offset: int = 0,
    limit: int = 100,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)

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


@router.get("/bulk")
async def bulk_note_form(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
    return templates.TemplateResponse(
        request=request, name="notes/bulk.html", context={"demo_note": None}
    )


@router.post("/bulk")
async def bulk_note(
    background_tasks: BackgroundTasks,
    request: Request,
    csv_file: UploadFile = File(...),
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
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


@router.get("/pagination")
async def read_notes_pagination(
    request: Request,
    search_term: str = Query(None),
    start_date: str = Query(None),
    end_date: str = Query(None),
    mood: str = Query(None),
    page: int = Query(1),
    limit: int = Query(20),
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info

    logger.debug(
        f"Searching for term: {search_term}, start_date: {start_date}, end_date: {end_date}, mood: {mood}"
    )

    # find search_term in columns: note, mood, tags, summary
    query = Select(Notes).where(
        (Notes.user_id == user_identifier)
        & (
            or_(
                Notes.note.contains(search_term) if search_term else True,
                Notes.summary.contains(search_term) if search_term else True,
                Notes.tags.contains(search_term) if search_term else True,
            )
        )
    )

    # filter by mood
    if mood:
        query = query.where(Notes.mood == mood)
    # filter by date range
    if start_date and end_date:
        query = query.where(
            (Notes.date_created >= start_date) & (Notes.date_created <= end_date)
        )
    # order and limit the results
    query = query.order_by(Notes.date_created.desc())
    offset = (page - 1) * limit
    notes = await db_ops.read_query(query=query, limit=limit, offset=offset)
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
    if offset == 0:
        current_count = limit
    else:
        current_count = limit + offset

    total_pages = -(-note_count // limit)  # Ceiling division
    prev_page_url = (
        f"/notes/pagination?page={page - 1}&limit={limit}" if page > 1 else None
    )
    next_page_url = (
        f"/notes/pagination?page={page + 1}&limit={limit}"
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


@router.get("/new")
async def new_note_form(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
    demo_note = get_note_demo_paragraph()
    logger.info("Generated demo note")
    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={"demo_note": demo_note}
    )


@router.post("/new")
async def create_note(
    request: Request,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
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

    return RedirectResponse(url=f"/notes/{data.pkid}", status_code=302)


@router.get("/{note_id}")
async def read_note(
    request: Request, note_id: str, user_info: tuple = Depends(get_user_info)
):
    user_identifier, user_timezone = user_info

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
        request=request, name="/notes/view.html", context={"note": note}
    )


# htmx get edit form
@router.get("/edit/{note_id}")
async def edit_note_form(
    request: Request,
    note_id: str,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info

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


# put /{note_id} requires user_identifier and note_id
@router.post("/edit/{note_id}")
async def update_note(
    request: Request,
    note_id: str,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
    form = await request.form()

    mood = form.get("mood")
    note = form.get("note")
    tags = form.get("tags")
    summary = form.get("summary")
    mood_analysis = form.get("mood_analysis")

    logger.debug(
        f"Received mood: {mood}, note: {note}, tags: {tags}, summary: {summary}, mood_analysis: {mood_analysis}"
    )

    # converts tags from a string to a list if tags is not None
    if tags:
        tags = tags.split(",")
        tags = {"tags": tags}

    # Create the note
    new_values = {
        "date_updated": datetime.utcnow(),
    }

    if summary:
        new_values["summary"] = summary
    if mood:
        new_values["mood"] = mood
    if tags:
        new_values["tags"] = tags
    if mood_analysis:
        new_values["mood_analysis"] = mood_analysis
    if note:
        new_values["note"] = note

    data = await db_ops.update_one(
        table=Notes, record_id=note_id, new_values=new_values
    )

    logger.info(f"Updated note with ID: {note_id}")

    return RedirectResponse(url=f"/notes/{data.pkid}", status_code=302)


# delete/{note_id}
@router.get("/delete/{note_id}")
async def delete_note_form(
    request: Request,
    note_id: str,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
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
    note_id: str,
    csrf_protect: CsrfProtect = Depends(),
    user_info: tuple = Depends(get_user_info),
):
    user_identifier, user_timezone = user_info
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
