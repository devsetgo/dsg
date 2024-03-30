# -*- coding: utf-8 -*-
import csv
from datetime import datetime

from dateutil.parser import parse
from loguru import logger
from tqdm import tqdm

from ..db_tables import Notes
from ..functions import ai
from ..resources import db_ops


async def read_notes_from_file(csv_file: list, user_id: str):

    validation_result = validate_csv_headers(csv_file)

    if validation_result["status"] != "success":
        logger.error(validation_result)
        return {"error": csv_file}

    notes: list = []
    for c in tqdm(csv_file, desc="Importing notes", unit="note"):

        date_created = c["date_created"]
        # convert date_created to datetime
        date_created = parse_date(date_created)

        mood = c["mood"]
        if mood not in ["positive", "negative", "neutral"]:
            mood = await ai.get_mood(content=c["my_note"])
        note = c["my_note"]

        try:
            analysis = await ai.get_analysis(content=note)
        except Exception as e:
            logger.error(e)
            analysis = {
                "tags": {"tags": ["error"]},
                "summary": "error",
                "mood_analysis": "error",
            }
        # Create the note
        note = Notes(
            mood=mood,
            note=note,
            tags=analysis["tags"]["tags"],
            summary=analysis["summary"],
            mood_analysis=analysis["mood_analysis"],
            date_created=date_created,
            user_id=user_id,
        )
        data = await db_ops.create_one(note)
        logger.info(data.to_dict())
        notes.append(data.to_dict())


def parse_date(date_created):
    try:
        # Try to parse the date with time
        return datetime.strptime(date_created, "%m/%d/%Y %H:%M")
    except ValueError:
        try:
            # If that fails, try to parse the date without time
            return datetime.strptime(date_created, "%m/%d/%Y")
        except ValueError:
            # If that also fails, try to parse the date with dateutil.parser.parse
            try:
                return parse(date_created)
            except ValueError:
                # If all attempts fail, return a default date or None
                return None


def validate_csv_headers(csv_reader: csv.DictReader):
    # confirm dictionary should have my_note (str), date_created (format 8/18/2013 19:35), mood (str positive, negative, neutral, unknown)
    expected_headers = ["my_note", "mood", "date_created"]
    headers = csv_reader.fieldnames

    if headers != expected_headers:
        missing_headers = [
            header for header in expected_headers if header not in headers
        ]
        extra_headers = [header for header in headers if header not in expected_headers]

        data = {
            "status": {
                "error": "Invalid CSV file",
                "missing_headers": missing_headers,
                "extra_headers": extra_headers,
            }
        }
        print(data)
        return data

    return {"status": "success"}

    # # decode csv_file_content
    # csv_file_content = csv_file.decode("utf-8").split("\n")
    # # get the headers
    # headers = csv_file_content[0].split(",")
    # # confirm the headers are correct "my_note", "date_created", "mood"
    # if headers != ["my_note", "date_created", "mood"]:
    #     return False
    # # convert notes to json
    # notes = []
    # for note in csv_file_content:
    #     note = note.split(",")
    #     print(note[0])
    #     print(note[1])
    #     print(note[2])

    # if len(note) == 3:
    #     # Get the tags and summary from OpenAI
    #     analysis = await ai.get_analysis(content=note[0])

    #     # Create the note
    #     note = Notes(
    #         mood=note[2],
    #         note=note[0],
    #         tags=analysis["tags"],
    #         summary=analysis["summary"],
    #         mood_analysis=analysis["mood_analysis"],
    #         user_id=user_id,
    #     )
    #     data = await db_ops.create_one(note)

    #     notes.append(data)

    # return notes
