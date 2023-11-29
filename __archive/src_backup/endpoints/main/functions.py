# -*- coding: utf-8 -*-
import random
import uuid
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from unittest import result

import httpx
from httpx_auth import Basic
from httpx_auth import HeaderApiKey
from loguru import logger

from settings import config_settings

client = httpx.AsyncClient()

api_key = Basic(config_settings.github_id, config_settings.github_token)


async def get_rate_limit():
    url = "https://api.github.com/rate_limit"
    r = await client.get(url, auth=api_key)
    data = r.json()
    logger.info(f"Rate Limit Data from Call: {data}")


async def call_github_repos() -> list:
    # Gets the most recent repos
    url = f"https://api.github.com/users/{config_settings.github_id}/repos?sort=pushed&per_page={config_settings.github_repo_limit}&type=public"
    r = await client.get(url, auth=api_key)
    logger.info(f"Fetching Repos for {config_settings.github_id}")
    data = r.json()
    logger.info(data)

    await get_rate_limit()

    if "message" in data:
        return {
            "message": "Github rate limit exceeded, try again later and I am surprised that it even hit the rate limit! But I am not paying for a higher rate limit. :-)"
        }
    else:
        results: list = []
        count: int = 1
        for d in data:
            if count <= 6 and d["archived"] == False:
                count += 1
                d["created_at"] = await format_time(d["created_at"])
                d["updated_at"] = await format_time(d["updated_at"])
                d["pushed_at"] = await format_time(d["pushed_at"])
                results.append(d)
        return results


async def call_github_user() -> list:
    # Gets the most recent repos
    url = f"https://api.github.com/users/{config_settings.github_id}"

    r = await client.get(url, auth=api_key)
    logger.info(f"Fetching Repos for {config_settings.github_id}")
    data = r.json()

    await get_rate_limit()

    if "message" in data:
        return {
            "message": "Github rate limit exceeded, try again later and I am surprised that. I am not paying for a higher rate limit. :-)"
        }
    else:
        data["created_at"] = await format_time(data["created_at"])
        data["updated_at"] = await format_time(data["updated_at"])

        return data


async def format_time(value):
    # print(value.strftime('%Y-%m-%d'))
    fd = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    simple_data = f"{fd.year}-{fd.month}-{fd.day}"
    return simple_data


def rate_limit_error():
    return x
