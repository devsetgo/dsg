# -*- coding: utf-8 -*-
"""
Background Tasks for OCR Processing

This module contains background tasks and scheduled jobs for the OCR PDF processing system.

Author:
    Mike Ryan

License:
    MIT License
"""

import asyncio

from loguru import logger

from .ocr_processing import cleanup_expired_files


async def schedule_ocr_cleanup_task():
    """
    Scheduled task to clean up expired OCR files.
    Runs every hour to check for and remove expired files.
    """
    while True:
        try:
            logger.info("Starting scheduled OCR cleanup task")
            cleaned_count = await cleanup_expired_files()
            logger.info(
                f"OCR cleanup task completed. Cleaned {cleaned_count} expired jobs"
            )

        except Exception as e:
            logger.error(f"Error in OCR cleanup task: {e}")

        # Wait for 1 hour before next cleanup
        await asyncio.sleep(3600)  # 3600 seconds = 1 hour


def start_background_tasks():
    """
    Start background tasks for OCR processing.
    This should be called when the application starts.
    """
    try:
        # Create and start the cleanup task
        asyncio.create_task(schedule_ocr_cleanup_task())
        logger.info("OCR background cleanup task started")

    except Exception as e:
        logger.error(f"Failed to start OCR background tasks: {e}")
