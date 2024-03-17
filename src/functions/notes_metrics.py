# -*- coding: utf-8 -*-

import asyncio
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from sqlalchemy import Select, and_, func, or_
from sqlalchemy.orm import joinedload

from ..db_tables import Notes, User
from ..functions import ai, date_functions
from ..functions.demo_functions import get_note_demo_paragraph, get_pypi_demo_list
from ..resources import db_ops, templates


async def get_metrics(user_identifier: str, user_timezone: str):
    logger.info("Getting metrics for user: {}", user_identifier)
    query = Select(Notes).where((Notes.user_id == user_identifier))
    notes = await db_ops.read_query(query=query, limit=10000, offset=0)
    notes = [note.to_dict() for note in notes]
    metrics = {
        "counts":{
        "mood_counts": dict(await mood_metrics(notes)),
        "note_count": format(len(notes), ","),
        "note_counts": await get_note_counts(notes),
        "tag_count": format(2,","),},
        "note_count_by_month": dict(await get_note_count_by_month(notes)),
        "mood_by_month": {k: dict(v) for k, v in (await mood_by_month(notes)).items()},
        "tags_common": "None",
    }
    logger.info("Metrics retrieved successfully for user: {}", user_identifier)
    return metrics


async def get_note_counts(notes: list):
    logger.info("Calculating note counts")
    word_count = 0
    char_count = 0
    note_count = len(notes)

    for note in notes:
        word_count += note["word_count"]
        char_count += note["character_count"]

    data = {
        "word_count": format(word_count, ","),
        "char_count": format(char_count, ","),
        "note_count": format(note_count, ","),
    }
    logger.info("Note counts calculated successfully")
    return data


async def get_note_count_by_month(notes: list):
    logger.info("Calculating note count by month")
    result = defaultdict(int)

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        result[month_year] += 1

    logger.info("Note count by month calculated successfully")
    return dict(result)


async def mood_metrics(notes: list):
    logger.info("Calculating mood metrics")
    mood_count = Counter([note["mood"] for note in notes])
    mood_count = {k: format(v, ",") for k, v in mood_count.items()}
    logger.info("Mood metrics calculated successfully")
    return dict(mood_count)


async def mood_by_month(notes: list):
    logger.info("Calculating mood by month")
    result = defaultdict(lambda: defaultdict(int))

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        result[month_year][note["mood"]] += 1

    logger.info("Mood by month calculated successfully")
    return {k: dict(v) for k, v in result.items()}