# -*- coding: utf-8 -*-
"""
This module provides functionality for importing notes from a CSV file into a database. It leverages OpenAI for creating summaries and performing analysis on the notes. The main functionality is encapsulated in the `read_notes_from_file` asynchronous function, which reads notes from a specified CSV file and stores them in the database using the user's identifier.

Functions:
    read_notes_from_file(csv_file: list, user_id: str) -> dict: Reads notes from a CSV file and stores them in the database.

Modules:
    csv: For reading from and writing to CSV files.
    itertools: Provides access to the iterator functions.
    datetime: For working with dates and times.
    dateutil.parser: For parsing dates and times from strings.
    dateutil.tz: For timezone definitions.
    loguru: For logging.
    sqlalchemy: For database interaction.
    tqdm: For providing a progress bar.
    tqdm.asyncio: For providing an asynchronous progress bar.
    db_tables: Defines the database tables.
    functions.ai: Contains functions related to AI operations.
    functions.notes_metrics: Contains functions for calculating metrics on notes.
    resources.db_ops: Contains database operations.

Example:
    To use this module to import notes from a CSV file, you would call the `read_notes_from_file` function with the path to your CSV file and the user identifier as arguments.

Author:
    Mike Ryan
    MIT Licensed
"""
import asyncio
import csv
import itertools
from datetime import datetime

from dateutil.parser import parse
from dateutil.tz import UTC
from loguru import logger
from sqlalchemy import Select
from tqdm import tqdm
from tqdm.asyncio import tqdm as async_tqdm

from ..db_tables import Notes
from ..functions import ai, notes_metrics
from ..resources import db_ops


async def read_notes_from_file(csv_file: list, user_id: str):
    """
    Reads notes from a CSV file and stores them in the database.

    Args:
        csv_file (list): The CSV file to read the notes from.
        user_id (str): The user identifier.

    Returns:
        dict: A dictionary containing an error message if the CSV file is invalid.
    """
    print("Beginning processing")
    # Validate the headers of the CSV file
    validation_result = validate_csv_headers(csv_file)
    logger.debug(validation_result)
    # If the validation fails, log an error and return an error message
    if validation_result["status"] != "success":
        logger.error(validation_result)
        return {"error": csv_file}

    # Create a copy of the CSV file and count the number of notes
    csv_file, csv_file_copy = itertools.tee(csv_file)
    note_count = sum(1 for _ in csv_file_copy)
    logger.info(f"Number of notes to process: {note_count}")
    # Initialize a list to store the IDs of the notes that need AI processing
    ai_ids = []
    count = 0

    # Iterate over each note in the CSV file
    for c in tqdm(csv_file, desc="Importing notes", total=note_count):
        count += 1
        # Parse the date created
        date_created = parse_date(c["date_created"])
        mood = c["mood"]
        logger.info(f"Processing note {count} for {date_created}")
        # If the mood is not one of the expected values, set it to "processing"
        if mood not in ["positive", "negative", "neutral"]:
            mood = "processing"

        note = c["my_note"]

        # Initialize the analysis with "processing" values
        analysis = {
            "tags": {"tags": ["processing"]},
            "summary": "processing",
            "mood_analysis": "processing",
        }

        # Create the note
        note = Notes(
            mood=mood,
            note=note,
            tags=analysis["tags"]["tags"],
            summary=analysis["summary"],
            mood_analysis=analysis["mood_analysis"],
            date_created=date_created,
            date_updated=date_created,
            user_id=user_id,
            ai_fix=True,
        )
        logger.debug(note)
        # Store the note in the database
        data = await db_ops.create_one(note)
        data = data.to_dict()
        logger.info(data)
        # Add the ID of the note to the list of IDs for AI processing
        ai_ids.append(data["pkid"])

    logger.info(f"Notes imoorted: {count}")
    # Process the notes with AI
    await process_ai(list_of_ids=ai_ids, user_identifier=user_id)
    # Update the notes metrics
    await notes_metrics.update_notes_metrics(user_id=user_id)


def parse_date(date_created):
    """
    Parses a date string into a datetime object.

    Args:
        date_created (str): The date string to parse.

    Returns:
        datetime: The parsed date, or None if the date string couldn't be parsed.
    """

    try:
        # Try to parse the date with time
        dt = datetime.strptime(date_created, "%m/%d/%Y %H:%M")
    except ValueError:
        try:
            # If that fails, try to parse the date without time
            dt = datetime.strptime(date_created, "%m/%d/%Y")
        except ValueError:
            try:
                # If that also fails, try to parse the date with dateutil.parser.parse
                dt = parse(date_created)
            except ValueError:
                # If all attempts fail, return None
                return None

    # If the datetime object is offset-aware, convert it to UTC and make it offset-naive
    if dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)

    return dt


async def process_note(
    note_id: str, semaphore: asyncio.Semaphore, user_identifier: str
):
    async with semaphore:
        try:
            query = Select(Notes).where(Notes.pkid == note_id)
            note = await db_ops.read_one_record(query=query)
            note = note.to_dict()
            logger.debug(f"AI Processing of note: {note}")

            mood = note["mood"]
            if mood not in ["positive", "negative", "neutral"]:
                mood = await ai.get_mood(content=note["note"])
                mood = mood["mood"]

            analysis = await ai.get_analysis(content=note["note"])
            logger.info(f"Received analysis from AI: {analysis}")

            note_update = {
                "tags": analysis["tags"]["tags"],
                "summary": analysis["summary"],
                "mood_analysis": analysis["mood_analysis"],
                "ai_fix": False,
                "mood": mood,
            }

            data = await db_ops.update_one(
                table=Notes, record_id=note["pkid"], new_values=note_update
            )
            data = data.to_dict()
            logger.info(f"Resubmitted note to AI with ID: {data['pkid']}")
        except Exception as e:
            logger.error(f"Error processing note ID {note_id}: {e}")


async def process_ai(list_of_ids: list, user_identifier: str):
    semaphore = asyncio.Semaphore(20)  # Limit to 20 concurrent tasks
    tasks = [
        process_note(note_id, semaphore, user_identifier) for note_id in list_of_ids
    ]
    for chunk in async_tqdm(
        [tasks[i : i + 20] for i in range(0, len(tasks), 20)], desc="AI processing"
    ):
        await asyncio.gather(*chunk)


def validate_csv_headers(csv_reader: csv.DictReader):
    """
    Validates the headers of a CSV file.

    Args:
        csv_reader (csv.DictReader): The CSV reader object.

    Returns:
        dict: A dictionary containing the status of the validation. If the validation fails,
              the dictionary also contains the missing and extra headers.
    """

    # Define the expected headers
    expected_headers = [
        "my_note",
        "mood",
        "date_created",
    ]

    # Get the actual headers from the CSV file
    headers = csv_reader.fieldnames
    logger.debug(f"Headers: {headers}")
    # If the actual headers don't match the expected headers
    if headers != expected_headers:
        # Find the headers that are missing from the CSV file
        missing_headers = [
            header for header in expected_headers if header not in headers
        ]

        # Find the headers that are in the CSV file but not in the expected headers
        extra_headers = [header for header in headers if header not in expected_headers]

        # Return a dictionary with the status and the missing and extra headers
        data = {
            "status": {
                "error": "Invalid CSV file",
                "missing_headers": missing_headers,
                "extra_headers": extra_headers,
            }
        }
        logger.error(data)
        return data

    # If the headers are correct, return a dictionary with the status
    return {"status": "success"}
