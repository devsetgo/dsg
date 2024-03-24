# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, or_

from ..db_tables import Notes
from ..functions import date_functions, notes_metrics
from ..functions.demo_functions import get_note_demo_paragraph
from ..resources import db_ops, templates

router = APIRouter()


@router.get("/")
async def read_notes(
    request: Request,
    offset: int = 0,
    limit: int = 100,
    csrf_protect: CsrfProtect = Depends(),
):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)

    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    # notes = await db_ops.read_query(
    #     query=Select(Notes)
    #     .where(Notes.user_id == user_identifier)
    #     .limit(limit)
    #     .offset(offset)
    # )
    # # convert list of notes to list of dictionaries using .to_dict()
    # notes = [note.to_dict() for note in notes]
    # # offset date_created and date_updated to user's timezone

    # # offset date_created and date_updated to user's timezone
    # for note in notes:
    #     note["date_created"] = await date_functions.timezone_update(
    #         user_timezone=user_timezone,
    #         date_time=note["date_created"],
    #         friendly_string=True,
    #     )
    #     note["date_updated"] = await date_functions.timezone_update(
    #         user_timezone=user_timezone,
    #         date_time=note["date_updated"],
    #         friendly_string=True,
    #     )

    metrics = await notes_metrics.get_metrics(
        user_identifier=user_identifier, user_timezone=user_timezone
    )

    context = {"user_identifier": user_identifier, "metrics": metrics}
    return templates.TemplateResponse(
        request=request, name="/notes/dashboard.html", context=context
    )


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
):
    await asyncio.sleep(0.2)
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        logger.info("Redirecting to login because user_identifier is None")
        return RedirectResponse(url="/users/login", status_code=302)
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
    # note_count = await db_ops.count_query(
    #     Select(Notes).where((Notes.user_id == user_identifier))
    # )
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


# new note form
@router.get("/new")
async def new_note_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    demo_note = get_note_demo_paragraph()
    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={"demo_note": demo_note}
    )


@router.post("/new")
async def create_note(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    form = await request.form()
    mood = form["mood"]
    note = form["note"]

    # Get the tags and summary from OpenAI
    # analysis = await ai.get_analysis(content=note)

    # Create the note
    note = Notes(
        mood=mood,
        note=note,
        # tags=analysis["tags"],
        # summary=analysis["summary"],
        user_id=user_identifier,
    )
    data = await db_ops.create_one(note)
    return RedirectResponse(url=f"/notes/{data.pkid}", status_code=302)


@router.get("/{note_id}")
async def read_note(request: Request, note_id: str):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)

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

    return templates.TemplateResponse(
        request=request, name="/notes/view.html", context={"note": note}
    )


# htmx get edit form
@router.get("/edit/{note_id}")
async def edit_note_form(
    request: Request, note_id: str, csrf_protect: CsrfProtect = Depends()
):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)

    query = Select(Notes).where(
        and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
    )
    note = await db_ops.read_one_record(query=query)
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

    return templates.TemplateResponse(
        request=request, name="/notes/edit.html", context={"note": note}
    )

# TODO: Why is this not working?
# put /{note_id} requires user_identifier and note_id
@router.put("/edit/{note_id}")
async def update_note(
    request: Request, note_id: str, csrf_protect: CsrfProtect = Depends()
):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    form = await request.form()
    mood = form["mood"]
    note = form["note"]
    print(note)
    # Get the tags and summary from OpenAI
    # analysis = await ai.get_analysis(content=note)

    # Create the note
    new_values = {"mood": mood, "note": note}
    print(values)
    data = await db_ops.update_one(table=Notes, record_id=note_id, new_values=new_values)
    # data = await db_ops.create_one(note)
    return RedirectResponse(url=f"/notes/{data.pkid}", status_code=302)


# delete/{note_id}


# number of notes
# number of words
# number of characters
# average number of words
# average number of characters
# number of notes by mood
# number of notes by tags
# number of notes by date range
# number of words by month
# number of characters by month
# trend of moods by month
# tag cloud
