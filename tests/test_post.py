# -*- coding: utf-8 -*-
# FILE: test_posts.py
import pytest
from fastapi.testclient import TestClient
from loguru import logger
from sqlalchemy import Select

from src.db_tables import Posts
from src.main import app
from src.resources import db_ops

client = TestClient(app, follow_redirects=True)


@pytest.mark.asyncio
async def test_get_posts(test_client, mock_login):
    response = test_client.get("/posts")
    assert response.status_code == 200
    assert (
        "<!DOCTYPE html>" in response.text
    )  # Check for a specific text in the HTML response


@pytest.mark.asyncio
async def test_edit_post(test_client, mock_login):
    # Fetch posts from the database
    posts = await db_ops.read_query(query=Select(Posts))
    logger.critical(posts)
    logger.critical(type(posts))
    try:
        posts = [post.to_dict() for post in posts]
    except Exception as ex:
        logger.critical(ex)
        pytest.fail(f"Error fetching posts from the database: {ex}")

    post_id = ""
    # Get the first post's UUID
    if posts:
        post = posts[0]
        post_id = post["pkid"]
    else:
        pytest.fail("No posts found in the database")

    post_data = {
        "title": "Updated Title",
        "summary": "Updated Summary",
        "content": "Updated Content",
        "category": "Updated Category",
        "tags": "updated,tags",
    }
    logger.critical(post_id)
    response = test_client.post(f"/posts/edit/{post_id}", data=post_data)
    # 9a87994b-8647-407b-9d7b-572a4a3b6013
    logger.critical(response.text)  # Log the response content
    assert response.status_code == 200
    assert (
        "<!DOCTYPE html>" in response.text
    )  # Check for a specific text in the HTML response
