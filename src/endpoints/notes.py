# -*- coding: utf-8 -*-

import uuid
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func,or_
from sqlalchemy.orm import joinedload

from ..db_tables import Notes, User
from ..functions import ai, date_functions
from ..functions.demo_functions import get_note_demo_paragraph, get_pypi_demo_list
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
    notes = await db_ops.read_query(
        query=Select(Notes)
        .where(Notes.user_id == user_identifier)
        .limit(limit)
        .offset(offset)
    )
    # convert list of notes to list of dictionaries using .to_dict()
    notes = [note.to_dict() for note in notes]
    # offset date_created and date_updated to user's timezone

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
    context = {"user_identifier": user_identifier, "notes": notes}
    return templates.TemplateResponse(
        request=request, name="/notes/dashboard.html", context=context
    )

# search /search
@router.get("/search")
async def search_notes(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)

    return templates.TemplateResponse(
        request=request, name="/notes/search.html", context={"user_identifier": user_identifier}
    )

# search /search
@router.post("/search")
async def get_notes(request: Request, search_term: str = Form(...), csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    user_timezone = request.session.get("timezone", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    # find search_term in columns: note, mood, tags, summary
    query = (
        Select(Notes)
        .where(
            (Notes.user_id == user_identifier) &
            (
                or_(
                    Notes.note.contains(search_term),
                    Notes.mood.contains(search_term),
                    Notes.tags.contains(search_term),
                    Notes.summary.contains(search_term)
                )
            )
        )
        .order_by(Notes.date_created.desc())
        .limit(100)
    )
    notes = await db_ops.read_query(query=query)
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

    return templates.TemplateResponse(
        request=request, name="/notes/search_term.html", context={"user_identifier": user_identifier, "notes": notes}
    )

# new note form
@router.get("/new")
async def new_note_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    demo_note = get_note_demo_paragraph()
    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={"demo_note": demo_note}
    )


@router.post("/new")
async def create_note(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
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
        request=request, name="/notes/edit.html", context={"note": note.to_dict()}
    )


# put /{note_id} requires user_identifier and note_id
@router.put("/{note_id}")
async def update_note(
    request: Request, note_id: str, csrf_protect: CsrfProtect = Depends()
):
    user_identifier = request.session.get("user_identifier", None)
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
        date_updated=datetime.utc(),
    )
    data = await db_ops.create_one(note)
    return RedirectResponse(url=f"/notes/{data.pkid}", status_code=302)


# delete/{note_id}

# metrics /metrics
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
