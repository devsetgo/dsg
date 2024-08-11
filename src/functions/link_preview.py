# -*- coding: utf-8 -*-
"""

"""

from ..resources import db_ops
from loguru import logger
from sqlalchemy import Select, asc, func, or_
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import io
from ..db_tables import WebLinks

import httpx

client = httpx.AsyncClient()

async def url_status(url: str) -> bool:
    """
    Checks the status of the given URL.

    Args:
        url (str): The URL to check.

    Returns:
        bool: True if the URL is not reachable (i.e., status code is not 2xx or 3xx), False otherwise.
    """

    try:
        response = await client.get(url)
        print(response.status_code)
        if response.status_code < 400:
            return True
        return False
    except Exception as e:
        return True


async def save_preview_image(pkid: str, image: bytes):
    try:
        update = await db_ops.update_one(
            table=WebLinks,
            new_values={
                "image_preview_data": image,
            },
            record_id=pkid,
        )
    except Exception as e:
        error: str = f"Error saving preview image: {e}"
        logger.error(error)


async def capture_full_page_screenshot(url: str, pkid: str) -> bytes:
    """
    Captures a full-page screenshot of the given URL and returns the image data as bytes.

    Args:
        url (str): The URL of the webpage to capture.

    Returns:
        bytes: The image data of the screenshot.
    """

    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    chrome_options.binary_location = "/usr/bin/google-chrome"  # Path to Chrome binary

    # Initialize the Chrome driver
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=chrome_options
    )

    try:
        # Navigate to the URL
        driver.get(url)

        # Set the window size to the full page
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.body.offsetHeight, "
            "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
            "document.documentElement.offsetHeight);"
        )
        driver.set_window_size(1920, total_height)

        # Capture the screenshot
        screenshot_as_bytes = driver.get_screenshot_as_png()
        await save_preview_image(pkid=pkid, image=screenshot_as_bytes)
    finally:
        driver.quit()
