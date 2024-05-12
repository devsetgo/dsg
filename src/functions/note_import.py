# -*- coding: utf-8 -*-
import asyncio
import csv
from datetime import datetime

from dateutil.parser import parse
from loguru import logger
from tqdm import tqdm

from ..db_tables import Notes
from ..functions import ai, notes_metrics
from ..resources import db_ops
from sqlalchemy import Select, Text, and_, between, cast, extract, or_


async def read_notes_from_file(csv_file: list, user_id: str):

    print("Beging processing")
    validation_result = validate_csv_headers(csv_file)

    if validation_result["status"] != "success":
        logger.error(validation_result)
        return {"error": csv_file}

    csv_data = list(csv_file)
    note_count = len(csv_data)
    print(note_count)
    
    ai_ids = []

    count = 0

    for c in tqdm(csv_file, desc="Importing notes"):
        count += 1
        
        logger.info(f"Processing note {count}")
        date_created = c["date_created"]
        # convert date_created to datetime
        date_created = parse_date(date_created)
        mood = c["mood"]
        if mood not in ["positive", "negative", "neutral"]:
            mood = await ai.get_mood(content=c["my_note"])
            mood = mood["mood"]
        note = c["my_note"]

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
        )
        data = await db_ops.create_one(note)
        data = data.to_dict()
        logger.info(data)
        ai_ids.append(data["pkid"])
        # notes.append(data.to_dict())
        # await notes_metrics.update_notes_metrics(user_identifier=user_id)

    await process_ai(list_of_ids=ai_ids, user_identifier=user_id)

async def process_ai(list_of_ids: list,user_identifier:str):

    for note_id in tqdm(list_of_ids, desc="AI processing"):
        query = Select(Notes).where(
            and_(Notes.user_id == user_identifier, Notes.pkid == note_id)
        )
        note = await db_ops.read_one_record(query=query)
        note = note.to_dict()

        # Get the tags and summary from OpenAI
        analysis = await ai.get_analysis(content=note["note"])
        logger.info(f"Received analysis from AI: {analysis}")
        # Create the note
        note_update = {
            "tags": analysis["tags"]["tags"],
            "summary": analysis["summary"],
            "mood_analysis": analysis["mood_analysis"],
            # "ai_fix":False
        }

        data = await db_ops.update_one(
            table=Notes, record_id=note["pkid"], new_values=note_update
        )
        data = data.to_dict()
        logger.info(f"Resubmited note to AI with ID: {data['pkid']}")


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
    expected_headers = [
        "my_note",
        "mood",
        "date_created",
    ]
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
        return data

    return {"status": "success"}
