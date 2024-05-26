# -*- coding: utf-8 -*-

import datetime
import json
import logging
import statistics
from collections import Counter, defaultdict, deque

from loguru import logger
from sqlalchemy import Select
from tqdm import tqdm

from ..db_tables import NoteMetrics, Notes
from ..resources import db_ops
from ..settings import settings


async def all_note_metrics():
    # Log the start of the function
    logger.info("Starting all_note_metrics function")

    # Select all notes
    query = Select(Notes)
    notes = await db_ops.read_query(query=query)

    # Convert each note to a dictionary
    note_list = [note.to_dict() for note in notes]

    # Initialize an empty list to store unique user IDs
    user_list: list = []
    for n in note_list:
        # If the user ID is not already in the list, add it
        if n["user_id"] not in user_list:
            user_list.append(n["user_id"])

    # Log the number of unique users found
    logger.info(f"Found {len(user_list)} unique users")

    # Process each user
    for u in tqdm(user_list, desc="Processing users for note metrics", leave=False):
        # Log the user ID of the user being processed
        logger.info(f"Processing user {u}")

        # Select the note metrics for the current user
        query = Select(NoteMetrics).where(NoteMetrics.user_id == u)
        nm = await db_ops.read_query(query=query)

        # Convert each note metric to a dictionary
        nm = [n.to_dict() for n in nm]

        # Log the note metrics before updating them
        logger.debug(f"Pre-note analysis: {nm}")

        # Update the note metrics for the current user
        await update_notes_metrics(user_id=u)

        # Select the updated note metrics for the current user
        query = Select(NoteMetrics).where(NoteMetrics.user_id == u)
        nm = await db_ops.read_query(query=query)

        # Convert each updated note metric to a dictionary
        nm = [n.to_dict() for n in nm]
        # Log the updated note metrics
        logger.debug(f"Post-note analysis: {nm}")

    # Log the end of the function
    logger.info("Finished all_note_metrics function")


async def update_notes_metrics(user_id: str):
    logger.critical("background task for metrics")

    query_metric = Select(NoteMetrics).where(NoteMetrics.user_id == user_id)
    metric_data = await db_ops.read_one_record(query=query_metric)
    query = Select(Notes).where((Notes.user_id == user_id))
    notes = await db_ops.read_query(query=query, limit=100000, offset=0)
    notes = [note.to_dict() for note in notes]

    mood_metric = await mood_metrics(notes=notes)

    total_unique_tag_count = await get_total_unique_tag_count(notes=notes)

    note_counts = await get_note_counts(notes=notes)

    metrics = await get_metrics(user_identifier=user_id, user_timezone="UTC")

    if metric_data is None:
        note_metrics = NoteMetrics(
            word_count=note_counts["word_count"],
            note_count=note_counts["note_count"],
            character_count=note_counts["char_count"],
            mood_metric=mood_metric,
            total_unique_tag_count=total_unique_tag_count,
            metrics=metrics,
            user_id=user_id,
        )
        result = await db_ops.create_one(note_metrics)
    else:
        note_metrics = {
            "word_count": note_counts["word_count"],
            "note_count": note_counts["note_count"],
            "character_count": note_counts["char_count"],
            "mood_metric": mood_metric,
            "total_unique_tag_count": total_unique_tag_count,
            "metrics": metrics,
            "user_id": user_id,
        }
        # Update the database
        result = await db_ops.update_one(
            table=NoteMetrics, record_id=metric_data.pkid, new_values=note_metrics
        )
    logger.critical(result)


async def get_metrics(user_identifier: str, user_timezone: str):
    logger.info("Getting metrics for user: {}", user_identifier)
    query = Select(Notes).where((Notes.user_id == user_identifier))
    notes = await db_ops.read_query(query=query, limit=10000, offset=0)
    notes = [note.to_dict() for note in notes]
    metrics = {
        # "counts": {
        #     "mood_counts": dict(await mood_metrics(notes=notes)),
        #     "note_count": format(len(notes), ","),
        #     "note_counts": await get_note_counts(notes=notes),
        #     "tag_count": format(await get_total_unique_tag_count(notes=notes), ","),
        # },
        "note_count_by_year": await get_note_count_by_year(notes),
        "note_count_by_month": await get_note_count_by_month(notes),
        "note_count_by_week": await get_note_count_by_week(notes),
        "mood_by_month": {k: dict(v) for k, v in (await mood_by_month(notes)).items()},
        "mood_trend_by_month": await mood_trend_by_mean_month(notes),
        "mood_trend_by_median_month": await mood_trend_by_median_month(notes),
        "mood_trend_by_rolling_mean_month": await mood_trend_by_rolling_mean_month(
            notes
        ),
        "mood_analysis_trend_by_mean_month": await mood_analysis_trend_by_mean_month(
            notes=notes
        ),
        "tags_common": await get_tag_count(notes=notes),
        # "notes": notes,
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
        "word_count": word_count,
        "char_count": char_count,
        "note_count": note_count,
    }
    logger.info("Note counts calculated successfully")
    return data


async def mood_metrics(notes: list):
    logger.info("Calculating mood metrics")
    mood_count = Counter([note["mood"] for note in notes])
    mood_count = dict(mood_count.items())
    logger.info("Mood metrics calculated successfully")
    return mood_count


async def get_total_unique_tag_count(notes: list):
    # example of notes.tags
    # 'tags': ['handed', 'sleepy', 'nutmeg'],
    tags = [tag for note in notes for tag in note["tags"]]
    tag_count = Counter(tags)
    return len(tag_count)


# charting data metrics
async def get_tag_count(notes: list):
    tags = [tag.capitalize() for note in notes for tag in note["tags"]]
    tag_count = Counter(tags)

    # Sort the tag_count dictionary by its values in descending order
    tag_count = dict(sorted(tag_count.items(), key=lambda item: item[1], reverse=True))

    # Limit the result to the top 20 tags
    tag_count = dict(list(tag_count.items())[:30])

    return json.dumps(tag_count)


async def get_note_count_by_year(notes: list):
    logger = logging.getLogger(__name__)
    logger.info("Calculating note count and word count by year")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        year = note["date_created"].strftime("%Y")
        result[year]["note_count"] += 1
        result[year]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year) from oldest to newest
    result = dict(
        sorted(
            result.items(), key=lambda item: datetime.datetime.strptime(item[0], "%Y")
        )
    )

    logger.info("Note count and word count by year calculated successfully")
    return json.dumps(result)


async def get_note_count_by_month(notes: list):
    logger = logging.getLogger(__name__)
    logger.info("Calculating note count and word count by month")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        result[month_year]["note_count"] += 1
        result[month_year]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    logger.info("Note count and word count by month calculated successfully")
    return json.dumps({month_year: dict(data) for month_year, data in result.items()})


async def get_note_count_by_week(notes: list):
    logger = logging.getLogger(__name__)
    logger.info("Calculating note count and word count by week")
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    for note in notes:
        week_year = note["date_created"].isocalendar()[0:2]  # Get year and week number
        week_year_str = f"{week_year[0]}-{week_year[1]:02d}"  # Convert the tuple to a string in the format "YYYY-Www"
        result[week_year_str]["note_count"] += 1
        result[week_year_str]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year-week) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%W"),
        )
    )

    logger.info("Note count and word count by week calculated successfully")
    return json.dumps(
        {week_year_str: dict(data) for week_year_str, data in result.items()}
    )


async def mood_by_month(notes: list):
    logger.info("Calculating mood by month")
    result = defaultdict(lambda: defaultdict(int))

    # Sort notes by date_created from oldest to newest
    notes = sorted(notes, key=lambda note: note["date_created"])

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        result[month_year][note["mood"]] += 1

    # Sort the result dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    logger.info("Mood by month calculated successfully")
    return result


async def mood_trend_by_mean_month(notes: list):
    logger.info("Calculating mood trend by month")
    result = defaultdict(int)
    count = defaultdict(int)

    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")

        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"
        result[month_year] += mood_values[mood]
        count[month_year] += 1

    for month_year in result:
        result[month_year] = round(result[month_year] / count[month_year], 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    logger.info("Mood trend by month calculated successfully")
    return result


async def mood_analysis_trend_by_mean_month(notes: list):
    logger.info("Calculating mood analysis trend by month")
    result = defaultdict(int)
    count = defaultdict(int)

    # Step 1: Create a dictionary from the mood_analysis_weights list
    mood_weights_dict = dict(settings.mood_analysis_weights)

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        mood_word = note["mood_analysis"].lower()  # Use the correct field here
        if mood_word in mood_weights_dict:
            result[month_year] += mood_weights_dict[mood_word]
            count[month_year] += 1

    for month_year in result:
        result[month_year] = round(result[month_year] / count[month_year], 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    logger.info("Mood analysis trend by month calculated successfully")
    return result


async def mood_trend_by_median_month(notes: list):
    logger.info("Calculating mood trend by month")
    result = defaultdict(list)

    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"
        result[month_year].append(mood_values[mood])

    for month_year in result:
        result[month_year] = round(statistics.median(result[month_year]), 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    logger.info("Mood trend by month calculated successfully")
    return result


async def mood_trend_by_rolling_mean_month(notes: list):
    logger = logging.getLogger(__name__)
    logger.info("Calculating mood trend by month")
    result = defaultdict(int)
    count = defaultdict(int)
    rolling_avg = {}

    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"
        result[month_year] += mood_values[mood]

        count[month_year] += 1

    for month_year in result:
        result[month_year] = round(result[month_year] / count[month_year], 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    # Calculate 3-month rolling average
    months = deque(maxlen=3)
    for month_year, avg in result.items():
        months.append(avg)
        if len(months) == 3:
            rolling_avg[month_year] = round(sum(months) / len(months), 3)

    logger.info("Mood trend by month calculated successfully")
    return rolling_avg