# -*- coding: utf-8 -*-
from dataclasses import dataclass
import random
from unittest import result
import uuid
from datetime import datetime
from datetime import timedelta

from loguru import logger
import httpx
from settings import config_settings

client = httpx.AsyncClient()

async def call_github()->list:
    # Gets the most recent repos
    url = f"https://api.github.com/users/{config_settings.githud_id}/repos?sort=\
    updated&per_page={10}&type=public"

    r = await client.get(url)
    logger.info(f"Fetching Repos for {config_settings.githud_id}")
    data = r.json()
    for d in data:
        print(d['name'])
    return data