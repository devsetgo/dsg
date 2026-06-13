# -*- coding: utf-8 -*-
"""

Author:
    Mike Ryan
    MIT Licensed
"""
import datetime
import json
import statistics
from collections import Counter, defaultdict, deque
from typing import Any

from loguru import logger
from sqlalchemy import Select
from tqdm import tqdm

from ..db_tables import NoteMetrics, Notes
from ..resources import db_ops
from ..settings import settings


def _metrics_note_from_model(note: Notes) -> dict[str, Any]:
    return {
        "date_created": note.date_created,
        "word_count": note.word_count or 0,
        "character_count": note.character_count or 0,
        "mood": note.mood or "neutral",
        "mood_analysis": note.mood_analysis or "neutral",
        "tags": note.tags or [],
        "ai_fix": bool(note.ai_fix),
    }


def _sort_by_period(data: dict[str, Any], period_format: str) -> dict[str, Any]:
    return dict(
        sorted(
            data.items(),
            key=lambda item: datetime.datetime.strptime(item[0], period_format),
        )
    )


def _compute_writing_streaks(unique_dates: set[datetime.date]) -> dict[str, int]:
    if not unique_dates:
        return {"current": 0, "longest": 0}

    today = datetime.datetime.now(datetime.timezone.utc).date()
    current = 0
    cursor = today
    while cursor in unique_dates:
        current += 1
        cursor -= datetime.timedelta(days=1)

    longest = 0
    running = 0
    previous = None
    for day in sorted(unique_dates):
        if previous is None or (day - previous).days == 1:
            running += 1
        else:
            running = 1
        if running > longest:
            longest = running
        previous = day

    return {"current": current, "longest": longest}


def _compute_milestones(
    note_count: int, longest_streak: int, unique_days: int, notes: list[dict[str, Any]]
) -> list[str]:
    milestones = []

    note_milestones = [10, 50, 100, 250, 500, 1000, 2500, 5000]
    for threshold in note_milestones:
        if note_count >= threshold:
            milestones.append(f"{threshold} notes written")

    streak_milestones = [7, 14, 30, 60, 100, 365]
    for threshold in streak_milestones:
        if longest_streak >= threshold:
            milestones.append(f"{threshold}-day writing streak")

    day_milestones = [30, 100, 365, 730, 1000]
    for threshold in day_milestones:
        if unique_days >= threshold:
            milestones.append(f"Wrote on {threshold} unique days")

    if notes:
        first_date = min(note["date_created"] for note in notes)
        years_active = max(
            0,
            (datetime.datetime.now(datetime.timezone.utc).date() - first_date.date()).days
            // 365,
        )
        if years_active >= 1:
            milestones.append(f"Journaling for {years_active} years")

    return milestones


async def _compute_metrics_bundle(notes: list[dict[str, Any]]) -> dict[str, Any]:
    mood_values = {"negative": -1, "neutral": 0, "positive": 1}
    mood_weights_dict = dict(settings.mood_analysis_weights)

    word_count = 0
    char_count = 0
    ai_fix_count = 0
    mood_count = Counter()
    raw_tag_counter = Counter()
    display_tag_counter = Counter()

    by_year = defaultdict(lambda: {"note_count": 0, "word_count": 0})
    by_month = defaultdict(lambda: {"note_count": 0, "word_count": 0})
    by_week = defaultdict(lambda: {"note_count": 0, "word_count": 0})
    mood_by_month_counts = defaultdict(lambda: defaultdict(int))

    mood_sum_by_month = defaultdict(float)
    mood_count_by_month = defaultdict(int)
    mood_values_by_month = defaultdict(list)
    mood_analysis_sum_by_month = defaultdict(float)
    mood_analysis_count_by_month = defaultdict(int)
    weekday_activity = defaultdict(int)
    hour_activity = defaultdict(int)
    mood_tag_counts = {
        "positive": Counter(),
        "neutral": Counter(),
        "negative": Counter(),
    }
    recent_tag_counts = Counter()
    prior_tag_counts = Counter()
    unique_written_dates: set[datetime.date] = set()

    latest_created = (
        max(note["date_created"] for note in notes)
        if notes
        else datetime.datetime.now(datetime.timezone.utc)
    )
    recent_start = latest_created - datetime.timedelta(days=90)
    prior_start = recent_start - datetime.timedelta(days=90)

    for note in notes:
        created = note["date_created"]
        note_word_count = note["word_count"] or 0
        note_char_count = note["character_count"] or 0
        mood_raw = note["mood"] or "neutral"
        mood_normalized = mood_raw.lower()
        mood_analysis = (note["mood_analysis"] or "").lower()

        if mood_normalized not in mood_values:
            mood_normalized = "neutral"

        tags = note.get("tags") or []
        created_date = created.date()

        word_count += note_word_count
        char_count += note_char_count
        if note.get("ai_fix"):
            ai_fix_count += 1

        mood_count[mood_raw] += 1

        year = created.strftime("%Y")
        month = created.strftime("%Y-%m")
        week_year = created.isocalendar()[0:2]
        week = f"{week_year[0]}-{week_year[1]:02d}"

        by_year[year]["note_count"] += 1
        by_year[year]["word_count"] += note_word_count

        by_month[month]["note_count"] += 1
        by_month[month]["word_count"] += note_word_count

        by_week[week]["note_count"] += 1
        by_week[week]["word_count"] += note_word_count

        mood_by_month_counts[month][mood_raw] += 1

        mood_sum_by_month[month] += mood_values[mood_normalized]
        mood_count_by_month[month] += 1
        mood_values_by_month[month].append(mood_values[mood_normalized])

        if mood_analysis in mood_weights_dict:
            mood_analysis_sum_by_month[month] += mood_weights_dict[mood_analysis]
            mood_analysis_count_by_month[month] += 1

        weekday_activity[created.weekday()] += 1
        hour_activity[created.hour] += 1
        unique_written_dates.add(created_date)

        for tag in tags:
            tag_text = str(tag)
            tag_lower = tag_text.lower()
            raw_tag_counter[tag_lower] += 1
            display_tag = tag_text.capitalize()
            display_tag_counter[display_tag] += 1
            mood_tag_counts[mood_normalized][display_tag] += 1

            if created >= recent_start:
                recent_tag_counts[display_tag] += 1
            elif created >= prior_start:
                prior_tag_counts[display_tag] += 1

    by_year = _sort_by_period(dict(by_year), "%Y")
    by_month = _sort_by_period(dict(by_month), "%Y-%m")
    by_week = _sort_by_period(dict(by_week), "%Y-%W")
    mood_by_month_counts = _sort_by_period(
        {k: dict(v) for k, v in mood_by_month_counts.items()}, "%Y-%m"
    )

    mood_mean_by_month = {}
    for month, total in mood_sum_by_month.items():
        mood_mean_by_month[month] = round(total / mood_count_by_month[month], 3)
    mood_mean_by_month = _sort_by_period(mood_mean_by_month, "%Y-%m")

    mood_median_by_month = {}
    for month, values in mood_values_by_month.items():
        mood_median_by_month[month] = round(statistics.median(values), 3)
    mood_median_by_month = _sort_by_period(mood_median_by_month, "%Y-%m")

    rolling_avg = {}
    months = deque(maxlen=3)
    for month, avg in mood_mean_by_month.items():
        months.append(avg)
        rolling_avg[month] = round(sum(months) / len(months), 3)

    mood_analysis_mean_by_month = {}
    for month, total in mood_analysis_sum_by_month.items():
        mood_analysis_mean_by_month[month] = round(
            total / mood_analysis_count_by_month[month], 3
        )
    mood_analysis_mean_by_month = _sort_by_period(mood_analysis_mean_by_month, "%Y-%m")

    tags_common = dict(
        sorted(display_tag_counter.items(), key=lambda item: item[1], reverse=True)[:30]
    )

    weekday_labels = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    activity_by_day = {
        weekday_labels[index]: weekday_activity.get(index, 0) for index in range(7)
    }

    activity_by_hour = {f"{hour:02d}": hour_activity.get(hour, 0) for hour in range(24)}

    mood_tag_correlation = {
        mood: dict(counter.most_common(10)) for mood, counter in mood_tag_counts.items()
    }

    tag_deltas = []
    for tag in set(recent_tag_counts) | set(prior_tag_counts):
        delta = recent_tag_counts.get(tag, 0) - prior_tag_counts.get(tag, 0)
        if delta != 0:
            tag_deltas.append((tag, delta))

    rising_tags = dict(
        sorted([item for item in tag_deltas if item[1] > 0], key=lambda item: item[1], reverse=True)[:5]
    )
    falling_tags = dict(
        sorted([item for item in tag_deltas if item[1] < 0], key=lambda item: item[1])[:5]
    )

    mood_stability_score = round(
        statistics.pstdev(mood_mean_by_month.values()), 3
    ) if len(mood_mean_by_month) > 1 else 0.0

    writing_streak = _compute_writing_streaks(unique_written_dates)
    milestones = _compute_milestones(
        note_count=len(notes),
        longest_streak=writing_streak["longest"],
        unique_days=len(unique_written_dates),
        notes=notes,
    )

    word_trend_by_month = {
        month: {
            "total_words": data["word_count"],
            "avg_words_per_note": round(
                data["word_count"] / data["note_count"], 2
            ) if data["note_count"] else 0,
            "note_count": data["note_count"],
        }
        for month, data in by_month.items()
    }

    metrics = {
        "note_count_by_year": json.dumps(by_year),
        "note_count_by_month": json.dumps(by_month),
        "note_count_by_week": json.dumps(by_week),
        "mood_by_month": mood_by_month_counts,
        "mood_trend_by_month": mood_mean_by_month,
        "mood_trend_by_median_month": mood_median_by_month,
        "mood_trend_by_rolling_mean_month": rolling_avg,
        "mood_analysis_trend_by_mean_month": mood_analysis_mean_by_month,
        "tags_common": json.dumps(tags_common),
        "writing_streak": writing_streak,
        "activity_by_day_of_week": activity_by_day,
        "activity_by_hour": activity_by_hour,
        "mood_tag_correlation": mood_tag_correlation,
        "tag_trend": {"rising": rising_tags, "falling": falling_tags},
        "mood_stability_score": mood_stability_score,
        "milestones": milestones,
        "word_trend_by_month": word_trend_by_month,
    }

    return {
        "note_count": len(notes),
        "word_count": word_count,
        "char_count": char_count,
        "mood_metric": dict(mood_count),
        "total_unique_tag_count": len(raw_tag_counter),
        "ai_fix_count": ai_fix_count,
        "metrics": metrics,
    }


async def all_note_metrics():
    # Log the start of the function
    logger.info("Starting all_note_metrics function")

    # Fetch only user ids to avoid decrypting note content while enumerating users.
    query = Select(Notes.user_id)
    rows = await db_ops.read_query(query=query)
    user_set = set()
    for row in rows:
        user_id = row.user_id if hasattr(row, "user_id") else row[0]
        if user_id is not None:
            user_set.add(user_id)
    user_list = sorted(user_set)

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
    logger.debug("background task for metrics")
    started_at = datetime.datetime.utcnow()

    query_metric = Select(NoteMetrics).where(NoteMetrics.user_id == user_id)
    metric_data = await db_ops.read_one_record(query=query_metric)

    query = Select(Notes).where(Notes.user_id == user_id).limit(10000).offset(0)
    notes = await db_ops.read_query(query=query)
    notes = [_metrics_note_from_model(note) for note in notes]
    bundle = await _compute_metrics_bundle(notes=notes)

    if metric_data is None:
        note_metrics = NoteMetrics(
            word_count=bundle["word_count"],
            note_count=bundle["note_count"],
            character_count=bundle["char_count"],
            mood_metric=bundle["mood_metric"],
            total_unique_tag_count=bundle["total_unique_tag_count"],
            metrics=bundle["metrics"],
            ai_fix_count=bundle["ai_fix_count"],
            user_id=user_id,
        )
        result = await db_ops.create_one(note_metrics)
    else:
        note_metrics = {
            "word_count": bundle["word_count"],
            "note_count": bundle["note_count"],
            "character_count": bundle["char_count"],
            "mood_metric": bundle["mood_metric"],
            "total_unique_tag_count": bundle["total_unique_tag_count"],
            "metrics": bundle["metrics"],
            "user_id": user_id,
            "ai_fix_count": bundle["ai_fix_count"],
        }

        # Update the database
        result = await db_ops.update_one(
            table=NoteMetrics, record_id=metric_data.pkid, new_values=note_metrics
        )

    logger.debug(result)
    elapsed_ms = int((datetime.datetime.utcnow() - started_at).total_seconds() * 1000)
    logger.info("Note metrics updated for user {} in {}ms", user_id, elapsed_ms)


async def get_metrics(notes: list[dict[str, Any]], user_identifier: str = ""):
    logger.info("Getting metrics for user: {}", user_identifier)
    bundle = await _compute_metrics_bundle(notes=notes)
    logger.info("Metrics retrieved successfully for user: {}", user_identifier)
    return bundle["metrics"]


async def get_ai_fix_count(notes: list):
    fix_count = 0
    for note in notes:
        if note["ai_fix"]:
            fix_count += 1
    logger.debug(f"AI Fix Count: {fix_count}")

    return fix_count


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
            mood = "neutral"  # Default to neutral if mood not recognized
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
            mood = "neutral"  # Default to neutral if mood not recognized
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
    logger.info("Calculating mood trend by month")
    result = defaultdict(int)
    count = defaultdict(int)
    rolling_avg = {}

    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    for note in notes:
        month_year = note["date_created"].strftime("%Y-%m")
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"  # Default to neutral if mood not recognized
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
        rolling_avg[month_year] = round(sum(months) / len(months), 3)

    logger.info("Mood trend by month calculated successfully")
    return rolling_avg
