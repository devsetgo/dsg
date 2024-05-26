# -*- coding: utf-8 -*-

import datetime
import json
import statistics
from collections import Counter, defaultdict
from typing import Any, Dict, List

from loguru import logger
from sqlalchemy import Select

from ..db_tables import NoteMetrics, Notes
from ..resources import db_ops
from ..settings import settings


async def all_note_metrics() -> None:
    """
    Calculates and logs the number of unique users who have created notes.

    This function selects all notes, converts each note to a dictionary, and stores the unique user IDs in a list.
    It then logs the number of unique users found.
    """
    # Log the start of the function
    logger.info("Starting all_note_metrics function")

    # Select all notes
    query: Select = Select(Notes)
    notes: List[Notes] = await db_ops.read_query(query=query)

    # Convert each note to a dictionary
    note_list: List[Dict] = [note.to_dict() for note in notes]

    # Initialize an empty list to store unique user IDs
    user_list: List[int] = []
    for n in note_list:
        # If the user ID is not already in the list, add it
        if n["user_id"] not in user_list:
            user_list.append(n["user_id"])

    # Log the number of unique users found
    logger.info(f"Found {len(user_list)} unique users")


async def update_notes_metrics(user_id: str) -> Dict[str, Any]:
    """
    Updates the note metrics for a specific user.

    This function selects the note metrics for the specified user, calculates new metrics,
    and either creates a new note metrics record or updates the existing one.

    Args:
        user_id (str): The ID of the user for whom to update the note metrics.

    Returns:
        dict: The result of the database operation.
    """
    # Log the start of the function
    logger.critical("background task for metrics")

    # Select the note metrics for the specified user
    query_metric: Select = Select(NoteMetrics).where(NoteMetrics.user_id == user_id)
    metric_data: NoteMetrics = await db_ops.read_one_record(query=query_metric)

    # Select the notes for the specified user
    query: Select = Select(Notes).where((Notes.user_id == user_id))
    notes: List[Notes] = await db_ops.read_query(query=query, limit=100000, offset=0)

    # Convert each note to a dictionary
    notes: List[Dict[str, Any]] = [note.to_dict() for note in notes]

    # Calculate the mood metrics for the notes
    mood_metric: Dict[str, Any] = await mood_metrics(notes=notes)

    # Calculate the total unique tag count for the notes
    total_unique_tag_count: int = await get_total_unique_tag_count(notes=notes)

    # Calculate the note counts for the notes
    note_counts: Dict[str, int] = await get_note_counts(notes=notes)

    # Get the metrics for the user
    metrics: Dict[str, Any] = await get_metrics(user_identifier=user_id, user_timezone="UTC")

    if metric_data is None:
        # If no note metrics exist for the user, create a new note metrics record
        note_metrics: NoteMetrics = NoteMetrics(
            word_count=note_counts["word_count"],
            note_count=note_counts["note_count"],
            character_count=note_counts["char_count"],
            mood_metric=mood_metric,
            total_unique_tag_count=total_unique_tag_count,
            metrics=metrics,
            user_id=user_id,
        )
        result: Dict[str, Any] = await db_ops.create_one(note_metrics)
    else:
        # If note metrics exist for the user, update the existing note metrics record
        note_metrics: Dict[str, Any] = {
            "word_count": note_counts["word_count"],
            "note_count": note_counts["note_count"],
            "character_count": note_counts["char_count"],
            "mood_metric": mood_metric,
            "total_unique_tag_count": total_unique_tag_count,
            "metrics": metrics,
            "user_id": user_id,
        }
        # Update the database
        result: Dict[str, Any] = await db_ops.update_one(
            table=NoteMetrics, record_id=metric_data.pkid, new_values=note_metrics
        )

    # Log the result of the database operation
    logger.critical(result)

    # Return the result of the database operation
    return result


async def get_metrics(user_identifier: str, user_timezone: str) -> Dict[str, Any]:
    """
    Retrieves the metrics for a specific user.

    This function retrieves the metrics for the specified user based on their timezone.

    Args:
        user_identifier (str): The identifier of the user for whom to retrieve the metrics.
        user_timezone (str): The timezone of the user.

    Returns:
        dict: The metrics for the user.
    """
    # Log the user identifier
    logger.info("Getting metrics for user: {}", user_identifier)

    # Select the notes for the specified user
    query: Select = Select(Notes).where((Notes.user_id == user_identifier))

    # Read the query results
    notes: List[Notes] = await db_ops.read_query(query=query, limit=10000, offset=0)

    # Convert each note to a dictionary
    notes: List[Dict[str, Any]] = [note.to_dict() for note in notes]

    # Calculate the metrics for the notes
    metrics: Dict[str, Any] = {
        # "counts": {
        # Your code here...
    }

    # Return the metrics
    return metrics


async def get_note_counts(notes: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Calculates the word count, character count, and note count for a list of notes.

    This function iterates over each note in the list, incrementing the word count and character count
    for each note. It also counts the total number of notes.

    Args:
        notes (List[Dict[str, Any]]): A list of notes, where each note is represented as a dictionary.

    Returns:
        dict: A dictionary containing the word count, character count, and note count.
    """
    # Log the start of the function
    logger.info("Calculating note counts")

    # Initialize the word count, character count, and note count
    word_count = 0
    char_count = 0
    note_count = len(notes)

    # Iterate over each note
    for note in notes:
        # Increment the word count and character count for each note
        word_count += note["word_count"]
        char_count += note["character_count"]

    # Store the counts in a dictionary
    data = {
        "word_count": word_count,
        "char_count": char_count,
        "note_count": note_count,
    }

    # Log the successful calculation of the counts
    logger.info("Note counts calculated successfully")

    # Return the counts
    return data


async def mood_metrics(notes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates the mood metrics for a list of notes.

    This function iterates over each note in the list, analyzing the mood of each note and
    aggregating the mood metrics.

    Args:
        notes (List[Dict[str, Any]]): A list of notes, where each note is represented as a dictionary.

    Returns:
        dict: A dictionary containing the aggregated mood metrics.
    """
    # Log the start of the function
    logger.info("Calculating mood metrics")

    # Initialize the mood metrics
    mood_metrics = {
        "happy": 0,
        "sad": 0,
        "angry": 0,
        "neutral": 0,
    }

    # Iterate over each note
    for note in notes:
        # Analyze the mood of the note
        mood = await analyze_mood(note["text"])

        # Increment the corresponding mood metric
        mood_metrics[mood] += 1

    # Log the successful calculation of the mood metrics
    logger.info("Mood metrics calculated successfully")

    # Return the mood metrics
    return mood_metrics


async def get_total_unique_tag_count(notes: List[Dict[str, List[str]]]) -> int:
    """
    Calculates the total unique tag count for a list of notes.

    This function iterates over each note in the list, extracting the tags from each note and
    counting the number of unique tags.

    Args:
        notes (List[Dict[str, List[str]]]): A list of notes, where each note is represented as a dictionary
        containing a list of tags.

    Returns:
        int: The total unique tag count.
    """
    # Log the start of the function
    logger.info("Calculating total unique tag count")

    # Extract the tags from each note
    tags = [tag for note in notes for tag in note["tags"]]

    # Count the unique tags
    tag_count = Counter(tags)

    # Log the successful calculation of the total unique tag count
    logger.info("Total unique tag count calculated successfully")

    # Return the total unique tag count
    return len(tag_count)


async def get_tag_count(notes: List[Dict[str, List[str]]]) -> str:
    """
    Calculates the count of each tag for a list of notes and returns the top 30 tags.

    This function iterates over each note in the list, extracting the tags from each note and
    counting the occurrence of each tag. The tags are then sorted in descending order of their counts
    and the top 30 tags are returned.

    Args:
        notes (List[Dict[str, List[str]]]): A list of notes, where each note is represented as a dictionary
        containing a list of tags.

    Returns:
        str: A JSON string representing a dictionary of the top 30 tags and their counts.
    """
    # Log the start of the function
    logger.info("Calculating tag count")

    # Extract and capitalize the tags from each note
    tags = [tag.capitalize() for note in notes for tag in note["tags"]]

    # Count the tags
    tag_count = Counter(tags)

    # Sort the tag_count dictionary by its values in descending order
    tag_count = dict(sorted(tag_count.items(), key=lambda item: item[1], reverse=True))

    # Limit the result to the top 30 tags
    tag_count = dict(list(tag_count.items())[:30])

    # Log the successful calculation of the tag count
    logger.info("Tag count calculated successfully")

    # Return the tag count as a JSON string
    return json.dumps(tag_count)


async def get_note_count_by_year(notes: List[Dict[str, Union[str, int, datetime]]]) -> str:
    """
    Calculates the note count and word count by year for a list of notes.

    This function iterates over each note in the list, extracting the year from the date_created field
    and incrementing the note count and word count for that year.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a word_count field, and other fields.

    Returns:
        str: A JSON string representing a dictionary of the note count and word count by year.
    """
    # Log the start of the function
    logger.info("Calculating note count and word count by year")

    # Initialize the result dictionary
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    # Iterate over each note
    for note in notes:
        # Extract the year from the date_created field
        year = note["date_created"].strftime("%Y")

        # Increment the note count and word count for that year
        result[year]["note_count"] += 1
        result[year]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year) from oldest to newest
    result = dict(
        sorted(
            result.items(), key=lambda item: datetime.datetime.strptime(item[0], "%Y")
        )
    )

    # Log the successful calculation of the note count and word count by year
    logger.info("Note count and word count by year calculated successfully")

    # Return the result as a JSON string
    return json.dumps(result)


async def get_note_count_by_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> str:
    """
    Calculates the note count and word count by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and incrementing the note count and word count for that month.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a word_count field, and other fields.

    Returns:
        str: A JSON string representing a dictionary of the note count and word count by month.
    """
    # Log the start of the function
    logger.info("Calculating note count and word count by month")

    # Initialize the result dictionary
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Increment the note count and word count for that month
        result[month_year]["note_count"] += 1
        result[month_year]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    # Log the successful calculation of the note count and word count by month
    logger.info("Note count and word count by month calculated successfully")

    # Return the result as a JSON string
    return json.dumps({month_year: dict(data) for month_year, data in result.items()})


async def get_note_count_by_week(notes: List[Dict[str, Union[str, int, datetime]]]) -> str:
    """
    Calculates the note count and word count by week for a list of notes.

    This function iterates over each note in the list, extracting the week and year from the date_created field
    and incrementing the note count and word count for that week.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a word_count field, and other fields.

    Returns:
        str: A JSON string representing a dictionary of the note count and word count by week.
    """
    # Log the start of the function
    logger.info("Calculating note count and word count by week")

    # Initialize the result dictionary
    result = defaultdict(lambda: {"note_count": 0, "word_count": 0})

    # Iterate over each note
    for note in notes:
        # Extract the week and year from the date_created field
        week_year = note["date_created"].isocalendar()[0:2]  # Get year and week number
        week_year_str = f"{week_year[0]}-{week_year[1]:02d}"  # Convert the tuple to a string in the format "YYYY-Www"

        # Increment the note count and word count for that week
        result[week_year_str]["note_count"] += 1
        result[week_year_str]["word_count"] += note["word_count"]

    # Sort the dictionary by keys (year-week) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%W"),
        )
    )

    # Log the successful calculation of the note count and word count by week
    logger.info("Note count and word count by week calculated successfully")

    # Return the result as a JSON string
    return json.dumps({week_year_str: dict(data) for week_year_str, data in result.items()})


async def mood_by_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> Dict[str, Dict[str, int]]:
    """
    Calculates the mood count by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and incrementing the mood count for that month.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a mood field, and other fields.

    Returns:
        Dict[str, Dict[str, int]]: A dictionary representing the mood count by month.
    """
    # Log the start of the function
    logger.info("Calculating mood by month")

    # Initialize the result dictionary
    result = defaultdict(lambda: defaultdict(int))

    # Sort notes by date_created from oldest to newest
    notes = sorted(notes, key=lambda note: note["date_created"])

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Increment the mood count for that month
        result[month_year][note["mood"]] += 1

    # Sort the result dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    # Log the successful calculation of the mood count by month
    logger.info("Mood by month calculated successfully")

    # Return the result dictionary
    return result


async def mood_trend_by_mean_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> Dict[str, float]:
    """
    Calculates the average mood trend by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and incrementing the mood count for that month. The mood is represented as an integer (-1 for negative, 0 for neutral,
    1 for positive). The average mood for each month is then calculated.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a mood field, and other fields.

    Returns:
        Dict[str, float]: A dictionary representing the average mood trend by month.
    """
    # Log the start of the function
    logger.info("Calculating mood trend by month")

    # Initialize the result and count dictionaries
    result = defaultdict(int)
    count = defaultdict(int)

    # Define the mood values
    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Get the mood of the note, defaulting to "neutral" if the mood is not recognized
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"

        # Increment the mood count and the note count for that month
        result[month_year] += mood_values[mood]
        count[month_year] += 1

    # Calculate the average mood for each month
    for month_year in result:
        result[month_year] = round(result[month_year] / count[month_year], 3)

    # Log the successful calculation of the mood trend by month
    logger.info("Mood trend by month calculated successfully")

    # Return the result dictionary
    return result


async def mood_analysis_trend_by_mean_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> Dict[str, float]:
    """
    Calculates the average mood analysis trend by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and incrementing the mood analysis count for that month. The mood analysis is represented as an integer
    based on the mood_analysis_weights setting. The average mood analysis for each month is then calculated.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a mood_analysis field, and other fields.

    Returns:
        Dict[str, float]: A dictionary representing the average mood analysis trend by month.
    """
    # Log the start of the function
    logger.info("Calculating mood analysis trend by month")

    # Initialize the result and count dictionaries
    result = defaultdict(int)
    count = defaultdict(int)

    # Create a dictionary from the mood_analysis_weights list
    mood_weights_dict = dict(settings.mood_analysis_weights)

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Get the mood analysis of the note, defaulting to 0 if the mood analysis is not recognized
        mood_word = note["mood_analysis"].lower()
        if mood_word in mood_weights_dict:
            # Increment the mood analysis count and the note count for that month
            result[month_year] += mood_weights_dict[mood_word]
            count[month_year] += 1

    # Calculate the average mood analysis for each month
    for month_year in result:
        result[month_year] = round(result[month_year] / count[month_year], 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    # Log the successful calculation of the mood analysis trend by month
    logger.info("Mood analysis trend by month calculated successfully")

    # Return the result dictionary
    return result


async def mood_trend_by_median_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> Dict[str, float]:
    """
    Calculates the median mood trend by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and appending the mood value for that month. The mood is represented as an integer (-1 for negative, 0 for neutral,
    1 for positive). The median mood for each month is then calculated.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a mood field, and other fields.

    Returns:
        Dict[str, float]: A dictionary representing the median mood trend by month.
    """
    # Log the start of the function
    logger.info("Calculating mood trend by month")

    # Initialize the result dictionary
    result = defaultdict(list)

    # Define the mood values
    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Get the mood of the note, defaulting to "neutral" if the mood is not recognized
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"

        # Append the mood value for that month
        result[month_year].append(mood_values[mood])

    # Calculate the median mood for each month
    for month_year in result:
        result[month_year] = round(statistics.median(result[month_year]), 3)

    # Sort the dictionary by keys (year-month) from oldest to newest
    result = dict(
        sorted(
            result.items(),
            key=lambda item: datetime.datetime.strptime(item[0], "%Y-%m"),
        )
    )

    # Log the successful calculation of the mood trend by month
    logger.info("Mood trend by month calculated successfully")

    # Return the result dictionary
    return result


async def mood_trend_by_rolling_mean_month(notes: List[Dict[str, Union[str, int, datetime]]]) -> Dict[str, float]:
    """
    Calculates the rolling mean mood trend by month for a list of notes.

    This function iterates over each note in the list, extracting the month and year from the date_created field
    and incrementing the mood count for that month. The mood is represented as an integer (-1 for negative, 0 for neutral,
    1 for positive). The rolling mean mood for each month is then calculated.

    Args:
        notes (List[Dict[str, Union[str, int, datetime]]]): A list of notes, where each note is represented
        as a dictionary containing a date_created field, a mood field, and other fields.

    Returns:
        Dict[str, float]: A dictionary representing the rolling mean mood trend by month.
    """
    # Log the start of the function
    logger.info("Calculating mood trend by month")

    # Initialize the result, count, and rolling_avg dictionaries
    result = defaultdict(int)
    count = defaultdict(int)
    rolling_avg = {}

    # Define the mood values
    mood_values = {"negative": -1, "neutral": 0, "positive": 1}

    # Iterate over each note
    for note in notes:
        # Extract the month and year from the date_created field
        month_year = note["date_created"].strftime("%Y-%m")

        # Get the mood of the note, defaulting to "neutral" if the mood is not recognized
        mood = note["mood"].lower()
        if mood not in mood_values:
            mood = "neutral"

        # Increment the mood count for that month
        result[month_year] += mood_values[mood]
        count[month_year] += 1

        # Calculate the rolling mean mood for that month
        rolling_avg[month_year] = round(result[month_year] / count[month_year], 3)

    # Log the successful calculation of the mood trend by month
    logger.info("Mood trend by month calculated successfully")

    # Return the rolling_avg dictionary
    return rolling_avg
