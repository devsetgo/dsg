# -*- coding: utf-8 -*-
"""
This module contains the function to read notes from a CSV file and store them in the database.

OpenAI is used to create summary and perform analysis on the notes
"""
import csv
import itertools
from datetime import datetime

from dateutil.parser import parse
from loguru import logger
from sqlalchemy import Select, and_
from tqdm import tqdm

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

    # If the validation fails, log an error and return an error message
    if validation_result["status"] != "success":
        logger.error(validation_result)
        return {"error": csv_file}

    # Create a copy of the CSV file and count the number of notes
    csv_file, csv_file_copy = itertools.tee(csv_file)
    note_count = sum(1 for _ in csv_file_copy)

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
        # Store the note in the database
        data = await db_ops.create_one(note)
        data = data.to_dict()
        logger.info(data)
        # Add the ID of the note to the list of IDs for AI processing
        ai_ids.append(data["pkid"])

    # Process the notes with AI
    await process_ai(list_of_ids=ai_ids, user_identifier=user_id)
    # Update the notes metrics
    await notes_metrics.update_notes_metrics(user_id=user_id)


async def process_ai(list_of_ids: list, user_identifier: str):
    """
    Processes a list of notes using AI for mood analysis and tagging.

    Args:
        list_of_ids (list): The list of note IDs to process.
        user_identifier (str): The user identifier.

    Returns:
        None
    """
    # Iterate over each note ID in the list
    for note_id in tqdm(list_of_ids, desc="AI processing"):
        # Create a query to select the note with the given ID and user identifier
        query = Select(Notes).where(
            and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
        )
        # Execute the query and get the note
        note = await db_ops.read_one_record(query=query)
        # Convert the note to a dictionary
        note = note.to_dict()

        # Get the mood of the note
        mood = note["mood"]
        # If the mood is not one of the expected values, use AI to get the mood
        if mood not in ["positive", "negative", "neutral"]:
            mood = await ai.get_mood(content=note["note"])
            mood = mood["mood"]

        # Get the tags and summary from OpenAI
        analysis = await ai.get_analysis(content=note["note"])
        # Log the received analysis
        logger.info(f"Received analysis from AI: {analysis}")

        # Create a dictionary with the new values for the note
        note_update = {
            "tags": analysis["tags"]["tags"],
            "summary": analysis["summary"],
            "mood_analysis": analysis["mood_analysis"],
            "ai_fix": False,
            "mood": mood,
        }

        # Update the note in the database
        data = await db_ops.update_one(
            table=Notes, record_id=note["pkid"], new_values=note_update
        )
        # Convert the updated note to a dictionary
        data = data.to_dict()
        # Log the ID of the resubmitted note
        logger.info(f"Resubmited note to AI with ID: {data['pkid']}")


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
        return datetime.strptime(date_created, "%m/%d/%Y %H:%M")
    except ValueError:
        try:
            # If that fails, try to parse the date without time
            return datetime.strptime(date_created, "%m/%d/%Y")
        except ValueError:
            try:
                # If that also fails, try to parse the date with dateutil.parser.parse
                return parse(date_created)
            except ValueError:
                # If all attempts fail, return None
                return None


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
        return data

    # If the headers are correct, return a dictionary with the status
    return {"status": "success"}
