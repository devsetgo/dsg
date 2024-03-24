# -*- coding: utf-8 -*-

import json
from collections import Counter, defaultdict

from loguru import logger
from sqlalchemy import Select

from ..db_tables import Notes
from ..resources import db_ops


async def get_metrics(user_identifier: str, user_timezone: str):
    logger.info("Getting metrics for user: {}", user_identifier)
    query = Select(Notes).where((Notes.user_id == user_identifier))
    notes = await db_ops.read_query(query=query, limit=10000, offset=0)
    notes = [note.to_dict() for note in notes]
    metrics = {
        "counts": {
            "mood_counts": dict(await mood_metrics(notes=notes)),
            "note_count": format(len(notes), ","),
            "note_counts": await get_note_counts(notes=notes),
            "tag_count": format(await get_total_unique_tag_count(notes=notes), ","),
        },
        "note_count_by_year": await get_note_count_by_year(notes),
        "note_count_by_month": await get_note_count_by_month(notes),
        "note_count_by_week": await get_note_count_by_week(notes),
        "mood_by_month": {k: dict(v) for k, v in (await mood_by_month(notes)).items()},
        "tags_common": await get_tag_count(notes=notes),
        "notes": notes,
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


async def get_note_count_by_year(notes: list):
    logger.info("Calculating note count and word count by year")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        year = note["date_created"].strftime("%Y")
        result[year]["note_count"] += 1
        result[year]["word_count"] += note["word_count"]

    # Convert the defaultdict to a regular dict before returning
    result = {year: dict(data) for year, data in result.items()}

    logger.info("Note count and word count by year calculated successfully")
    return json.dumps(result)


async def get_note_count_by_month(notes: list):
    logger.info("Calculating note count and word count by month")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        result[month_year]["note_count"] += 1
        result[month_year]["word_count"] += note["word_count"]

    logger.info("Note count and word count by month calculated successfully")
    return json.dumps({month_year: dict(data) for month_year, data in result.items()})


async def get_note_count_by_week(notes: list):
    logger.info("Calculating note count and word count by week")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        week_year = note["date_created"].isocalendar()[0:2]  # Get year and week number
        week_year_str = f"{week_year[0]}-{week_year[1]}"  # Convert the tuple to a string in the format "YYYY-Www"
        result[week_year_str]["note_count"] += 1
        result[week_year_str]["word_count"] += note["word_count"]

    logger.info("Note count and word count by week calculated successfully")
    return json.dumps(
        {week_year_str: dict(data) for week_year_str, data in result.items()}
    )


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


# total unique count
async def get_total_unique_tag_count(notes: list):
    # example of notes.tags
    # 'tags': ['handed', 'sleepy', 'nutmeg'],
    tags = [tag for note in notes for tag in note["tags"]]
    tag_count = Counter(tags)
    return len(tag_count)


# Count of each tag
async def get_tag_count(notes: list):
    tags = [tag for note in notes for tag in note["tags"]]
    tag_count = Counter(tags)

    # Sort the tag_count dictionary by its values in descending order
    tag_count = dict(sorted(tag_count.items(), key=lambda item: item[1], reverse=True))

    # Limit the result to the top 20 tags
    tag_count = dict(list(tag_count.items())[:30])

    return json.dumps(tag_count)
