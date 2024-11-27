# FILE: test_posts.py
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.resources import db_ops
from sqlalchemy import Select
from src.db_tables import Posts
from loguru import logger

client = TestClient(app, follow_redirects=True)

@pytest.mark.asyncio
async def test_get_posts(test_client, mock_login):
    response = test_client.get("/posts")
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text  # Check for a specific text in the HTML response

@pytest.mark.asyncio
async def test_edit_post(test_client, mock_login):
    # Fetch posts from the database
    posts = await db_ops.read_query(query=Select(Posts))
    posts = [post.to_dict() for post in posts]
    logger.critical(posts)
    
    # Get the first post's UUID
    if posts:
        post = posts[0]
        post_id = post['pkid']
    else:
        pytest.fail("No posts found in the database")

    post_data = {
        "title": "Updated Title",
        "summary": "Updated Summary",
        "content": "Updated Content",
        "category": "Updated Category",
        "tags": "updated,tags"
    }
    response = test_client.post(f"/posts/edit/{post_id}", data=post_data)
    logger.critical(response.text)  # Log the response content
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text  # Check for a specific text in the HTML response