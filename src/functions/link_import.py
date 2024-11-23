# -*- coding: utf-8 -*-
"""

Author:
    Mike Ryan
    MIT Licensed
"""
import csv
import io

from loguru import logger
from sqlalchemy import Select
from tqdm import tqdm

from ..db_tables import WebLinks
from ..functions import ai, link_preview
from ..resources import db_ops

# class WebLink(BaseModel):
#     user_id: str
#     url: str
#     category: str
#     ai_fixe: bool = True


async def read_weblinks_from_file(csv_content: str, user_identifier: str):
    """
    Read weblinks from a CSV content string
    """
    csv_reader = csv.DictReader(io.StringIO(csv_content))
    data = list(csv_reader)

    link_pkids: list = []
    count = 0
    for i in data:
        count += 1
        # if count > 10:
        #     break
        public = True if i["public"] == "True" else False
        title = await ai.get_html_title(i["url"])
        if title == "Not Found":
            title = "Processing"
        link = WebLinks(
            title=title,
            summary="Processing",
            url=i["url"],
            category=i["category"],
            public=public,
            user_id=user_identifier,
            ai_fix=True,
        )
        data = await db_ops.create_one(link)
        logger.debug(data.pkid)
        link_pkids.append(data.pkid)

    logger.debug(link_pkids)
    await ai_process_pkids(link_pkids)
    await loop_pkids_for_images(link_pkids)


async def ai_process_pkids(pkids: list):
    """
    Process the AI for the given pkids
    """
    for pkid in tqdm(pkids, desc="AI Processing links"):
        record = await db_ops.read_one_record(
            Select(WebLinks).where(WebLinks.pkid == pkid)
        )

        if isinstance(record, dict):
            logger.error(f"Error creating link: {record}")
            continue

        link_update = {
            "ai_fix": False,
        }
        # title = await ai.get_html_title(record.url)
        logger.info(f"Processed link {record.pkid}")
        summary = await ai.get_url_summary(record.url)
        link_update["summary"] = summary["summary"]

        if record.title == "Processing":
            link_update["title"] = await ai.get_url_title(record.url)

        logger.info(link_update)
        data = await db_ops.update_one(
            table=WebLinks, record_id=pkid, new_values=link_update
        )
        logger.debug(f"Updated link data: {data}")

    return {"status": "success"}


# link_preview.capture_full_page_screenshot, url=url, pkid=data.pkid
async def loop_pkids_for_images(pkids: list):
    """
    Loop through the pkids and capture the full page screenshot
    """
    for pkid in tqdm(pkids, desc="Capturing full page screenshots"):
        data = await db_ops.read_one_record(
            Select(WebLinks).where(WebLinks.pkid == pkid)
        )
        if isinstance(data, dict):
            logger.error(f"Error creating link: {data}")
        else:
            await link_preview.capture_full_page_screenshot(
                url=data.url, pkid=data.pkid
            )

    return {"status": "success"}
