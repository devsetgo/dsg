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
from datetime import datetime, timedelta
from collections import Counter

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func
from sqlalchemy.orm import joinedload

from ..db_tables import Notes, User
from ..resources import db_ops, templates
from ..functions import ai
from ..functions.demo_functions import get_note_demo_paragraph, get_pypi_demo_list
router = APIRouter()


@router.get("/")
async def read_notes(
    request: Request,
    offset: int = 0,
    limit: int = 100,
    csrf_protect: CsrfProtect = Depends(),
):
    user_identifier = request.session.get("user_identifier", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    notes = await db_ops.read_query(
        query=Select(Notes)
        .where(Notes.user_id == user_identifier)
        .limit(limit)
        .offset(offset)
    )
    context = {"user_identifier": user_identifier, "notes": notes}

    return templates.TemplateResponse(
        request=request, name="/notes/dashboard.html", context=context
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
    analysis = await ai.get_analysis(content=note)

    # Create the note
    note = Notes(
        mood=mood,
        note=note,
        tags=analysis["tags"],
        summary=analysis["summary"],
        user_id=user_identifier,
    )
    data = await db_ops.create_one(note)
    return data


# new note form
@router.get("/new")
async def new_note_form(request: Request, csrf_protect: CsrfProtect = Depends()):
    user_identifier = request.session.get("user_identifier", None)
    if user_identifier is None:
        return RedirectResponse(url="/users/login", status_code=302)
    demo_note = get_note_demo_paragraph()
    return templates.TemplateResponse(
        request=request, name="notes/new.html", context={'demo_note': demo_note}
    )


# @router.get("/mynotes/{note_id}", response_model=schemas.Note)
# def read_note(note_id: int, db: Session = Depends(get_db)):
#     db_note = crud.get_note(db, note_id=note_id)
#     if db_note is None:
#         raise HTTPException(status_code=404, detail="Note not found")
#     return db_note

# @router.put("/mynotes/{note_id}", response_model=schemas.Note)
# def update_note(note_id: int, note: schemas.NoteCreate, db: Session = Depends(get_db)):
#     return crud.update_user_note(db=db, note_id=note_id, note=note)

# @router.delete("/mynotes/{note_id}")
# def delete_note(note_id: int, db: Session = Depends(get_db)):
#     crud.delete_user_note(db=db, note_id=note_id)
#     return {"detail": "Note deleted"}

# Additional endpoints for metrics and admin can be added here
