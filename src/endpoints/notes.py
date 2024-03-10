# create new API endpoint for notes
# the user id (user.pkid) is in the session [user_identifier]
# the endpoints should include the following for a user:
# 1. create a main page for the users notes
# 2. create a new note
# 3. get all notes for a user
# 4. get a single note for a user
# 5. update a single note for a user
# 6. delete a single note for a user
# 7. get all notes by mood and/or tags, date range, etc. for a user
# 8. get metrics for notes (word count, character count, etc.) for a user
# 9. get metrics for date range of notes (word count, character count, etc.) for a user
# 10. get admin only metrics for notes (word count, character count, etc.)

# class Notes(base_schema.SchemaBase, async_db.Base):
#     __tablename__ = "notes"  # Name of the table in the database
#     __tableargs__ = {"comment": "Notes that the user writes"}

#     # Define the columns of the table
#     mood = Column(String(50), unique=False, index=True)  # mood of note
#     note = Column(String(5000), unique=False, index=True)  # note
#     tags = Column(JSON)  # tags from OpenAI
#     summary = Column(String(500), unique=False, index=True)  # summary from OpenAI
#     # Define the parent relationship to the User class
#     user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
#     user = relationship(
#         "User", back_populates="Notes"
#     )  # Relationship to the User class

#     @property
#     def word_count(self):
#         return len(self.note.split())

#     @property
#     def character_count(self):
#         return len(self.note)

# -*- coding: utf-8 -*-

import uuid
from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func
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

# search /search

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
