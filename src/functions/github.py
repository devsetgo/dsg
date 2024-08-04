# -*- coding: utf-8 -*-
"""
This module contains functions to interact with the GitHub API.

It includes functions to get the rate limit, fetch repositories, and fetch user
data from GitHub. The results of these API calls are cached for an hour to avoid
hitting the rate limit.

Functions:
    get_rate_limit: Fetches the current rate limit from the GitHub API.
    call_github_repos: Fetches the most recent repositories of a user.
    call_github_user: Fetches the user data from GitHub. format_time: Formats
    the time received from the GitHub API.

Author:
    Mike Ryan
    MIT Licensed
"""
from datetime import datetime

import httpx
from async_lru import alru_cache
from httpx_auth import Basic
from loguru import logger

from ..settings import settings

client = httpx.AsyncClient()

api_key = Basic(settings.github_id, settings.github_token.get_secret_value())


# This function is used to fetch the most recent repositories of a user from the
# GitHub API It is cached for an hour to avoid hitting the rate limit
@alru_cache(ttl=3600, maxsize=32)
async def call_github_repos() -> list:
    # The URL for the GitHub API's user repositories endpoint
    url = f"https://api.github.com/users/{settings.github_id}/repos?sort=pushed&\
        per_page={settings.github_repo_limit}&type=public"

    # Make a GET request to the URL, using the API key for authentication
    r = await client.get(url, auth=api_key)

    # Log the action
    logger.info(f"Fetching Repos for {settings.github_id}")

    # Convert the response to JSON format
    data = r.json()

    # Log the data
    logger.info(data)

    # Check if the rate limit has been exceeded
    if "message" in data:
        return {
            "message": "Github rate limit exceeded, try again later and I am surprised\
                 that it even hit the rate limit! But I am not paying for a higher\
                     rate limit. :-)"
        }
    else:
        # Process the data and return the results
        results: list = []
        count: int = 1
        for d in data:
            if count <= 6 and d["archived"] is False:
                count += 1
                d["created_at"] = await format_time(d["created_at"])
                d["updated_at"] = await format_time(d["updated_at"])
                d["pushed_at"] = await format_time(d["pushed_at"])
                results.append(d)
        return results


# This function is used to fetch the user data from the GitHub API It is cached
# for an hour to avoid hitting the rate limit
@alru_cache(ttl=3600, maxsize=32)
async def call_github_user() -> list:
    # The URL for the GitHub API's user endpoint
    url = f"https://api.github.com/users/{settings.github_id}"

    # Make a GET request to the URL, using the API key for authentication
    r = await client.get(url, auth=api_key)

    # Log the action
    logger.info(f"Fetching Repos for {settings.github_id}")

    # Convert the response to JSON format
    data = r.json()

    # Check if the rate limit has been exceeded
    if "message" in data:
        return {
            "message": "Github rate limit exceeded, try again later and I am surprised\
                 that. I am not paying for a higher rate limit. :-)"
        }
    else:
        # Process the data and return the results
        data["created_at"] = await format_time(data["created_at"])
        data["updated_at"] = await format_time(data["updated_at"])

        return data


# This function is used to format the time received from the GitHub API
async def format_time(value):
    # Convert the time string to a datetime object
    fd = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")

    # Format the datetime object as a string
    simple_data = f"{fd.year}-{fd.month}-{fd.day}"

    return simple_data
