# -*- coding: utf-8 -*-

import uuid
from collections import Counter
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from fastapi import APIRouter, Depends, Form, Request, Query
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func, or_
from sqlalchemy.orm import joinedload


from ..db_tables import Notes, User
from ..functions import ai, date_functions
from ..functions.demo_functions import get_note_demo_paragraph, get_pypi_demo_list
from ..resources import db_ops, templates


# metrics /metrics
async def get_metrics(user_identifier:str, user_timezone:str):
    query = Select(Notes).where(
        (Notes.user_id == user_identifier))
    notes = await db_ops.read_query(query=query, limit=10000, offset=0)
    notes = [note.to_dict() for note in notes]


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
    metrics = {"mood_counts": await mood_metrics(notes), "note_count": len(notes), "mood_by_month": await mood_by_month(notes)}   
    return metrics

async def mood_metrics(notes:list):
    mood_count = Counter([note['mood'] for note in notes])
    print(mood_count)
    return mood_count



async def mood_by_month(notes:list):
    # Initialize a default dictionary to store the results
    result = defaultdict(lambda: defaultdict(int))

    # Iterate over the data
    for note in notes:
        # Extract the month and year from the note's date
        month_year = note['date_created'].strftime('%Y-%m')

        # Increment the count for the note's mood in the corresponding month-year
        result[month_year][note['mood']] += 1

    return dict(result)