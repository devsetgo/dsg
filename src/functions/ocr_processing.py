# -*- coding: utf-8 -*-
"""
OCR PDF Processing Module

This module handles OCR (Optical Character Recognition) processing for PDF files.
It provides functionality to convert PDFs to searchable PDFs with text extraction capabilities.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - ocrmypdf: For OCR processing
    - pathlib: For file path operations
    - asyncio: For asynchronous operations
    - loguru: For logging
"""

import asyncio
import os
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import ocrmypdf
from loguru import logger
from sqlalchemy import Select

from ..db_tables import OCRJob
from ..resources import db_ops


# Configure OCR directories
OCR_BASE_DIR = Path(__file__).parent.parent.parent / "pdf" / "data"
OCR_INPUT_DIR = OCR_BASE_DIR / "ocr-in"
OCR_OUTPUT_DIR = OCR_BASE_DIR / "ocr-out"

# Ensure directories exist
OCR_INPUT_DIR.mkdir(parents=True, exist_ok=True)
OCR_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


async def save_uploaded_pdf(uploaded_file, user_id: str) -> dict:
    """
    Save uploaded PDF file and create OCR job record.

    Args:
        uploaded_file: FastAPI UploadFile object
        user_id: User identifier

    Returns:
        dict: Job information including job_id and file paths
    """
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())

        # Create file paths
        original_filename = uploaded_file.filename
        file_extension = Path(original_filename).suffix

        # Generate unique filenames to avoid conflicts
        timestamp = int(time.time())
        safe_filename = f"{job_id}_{timestamp}{file_extension}"

        original_filepath = OCR_INPUT_DIR / safe_filename
        converted_filepath = (
            OCR_OUTPUT_DIR / f"{job_id}_{timestamp}_converted{file_extension}"
        )

        # Save the uploaded file
        content = await uploaded_file.read()
        with open(original_filepath, "wb") as f:
            f.write(content)

        file_size = len(content)

        # Set cleanup date (7 days from now)
        cleanup_after = datetime.utcnow() + timedelta(days=7)

        # Create OCR job record
        ocr_job = OCRJob(
            user_id=user_id,
            job_id=job_id,
            original_filename=original_filename,
            original_filepath=str(original_filepath),
            converted_filepath=str(converted_filepath),
            status="pending",
            file_size_original=file_size,
            cleanup_after=cleanup_after,
        )

        await db_ops.create_one(ocr_job)

        logger.info(f"Created OCR job {job_id} for user {user_id}")

        return {
            "job_id": job_id,
            "original_filepath": str(original_filepath),
            "converted_filepath": str(converted_filepath),
            "original_filename": original_filename,
            "file_size": file_size,
        }

    except Exception as e:
        logger.error(f"Error saving uploaded PDF: {e}")
        raise


async def process_ocr_pdf(job_id: str) -> bool:
    """
    Process PDF with OCR in a background task.

    Args:
        job_id: Unique job identifier

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get job details
        query = Select(OCRJob).where(OCRJob.job_id == job_id)
        job = await db_ops.read_one_record(query=query)

        if not job:
            logger.error(f"OCR job {job_id} not found")
            return False

        # Update status to processing
        await db_ops.update_one(
            table=OCRJob, record_id=job.pkid, new_values={"status": "processing"}
        )

        logger.info(f"Starting OCR processing for job {job_id}")
        start_time = time.time()

        # Run OCR processing
        await run_ocr_conversion(
            input_path=Path(job.original_filepath),
            output_path=Path(job.converted_filepath),
        )

        end_time = time.time()
        processing_duration = int(end_time - start_time)

        # Get converted file size
        converted_file_size = Path(job.converted_filepath).stat().st_size

        # Update job as completed
        await db_ops.update_one(
            table=OCRJob,
            record_id=job.pkid,
            new_values={
                "status": "completed",
                "processing_duration": processing_duration,
                "file_size_converted": converted_file_size,
            },
        )

        logger.info(
            f"OCR processing completed for job {job_id} in {processing_duration} seconds"
        )
        return True

    except Exception as e:
        logger.error(f"Error processing OCR for job {job_id}: {e}")

        # Update job as failed
        try:
            query = Select(OCRJob).where(OCRJob.job_id == job_id)
            job = await db_ops.read_one_record(query=query)
            if job:
                await db_ops.update_one(
                    table=OCRJob,
                    record_id=job.pkid,
                    new_values={"status": "failed", "error_message": str(e)},
                )
        except Exception as update_error:
            logger.error(f"Failed to update job status: {update_error}")

        return False


async def run_ocr_conversion(input_path: Path, output_path: Path):
    """
    Run OCR conversion using ocrmypdf.

    Args:
        input_path: Path to input PDF
        output_path: Path to output PDF
    """

    def _run_ocr():
        """Synchronous OCR processing function."""
        ocrmypdf.ocr(
            input_path,
            output_path,
            deskew=True,
            rotate_pages=True,
            clean=True,
            language="eng",  # Can be made configurable later: "eng+spa" etc.
            output_type="pdfa",  # PDF/A for archiving and text extraction
            force_ocr=False,  # Only OCR if no text is detected
            skip_text=False,  # Don't skip pages that already have text
        )

    # Run OCR in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _run_ocr)


async def get_ocr_job_status(job_id: str, user_id: str) -> Optional[dict]:
    """
    Get OCR job status for a specific user.

    Args:
        job_id: Job identifier
        user_id: User identifier

    Returns:
        dict: Job status information or None if not found
    """
    try:
        query = Select(OCRJob).where(
            (OCRJob.job_id == job_id) & (OCRJob.user_id == user_id)
        )
        job = await db_ops.read_one_record(query=query)

        if not job:
            return None

        job_dict = job.to_dict()

        # Add additional computed fields
        if job_dict["status"] == "completed":
            job_dict["download_available"] = Path(
                job_dict["converted_filepath"]
            ).exists()
        else:
            job_dict["download_available"] = False

        return job_dict

    except Exception as e:
        logger.error(f"Error getting OCR job status: {e}")
        return None


async def get_user_ocr_jobs(user_id: str, limit: int = 10) -> list:
    """
    Get recent OCR jobs for a user.

    Args:
        user_id: User identifier
        limit: Maximum number of jobs to return

    Returns:
        list: List of OCR jobs
    """
    try:
        query = (
            Select(OCRJob)
            .where(OCRJob.user_id == user_id)
            .order_by(OCRJob.date_created.desc())
            .limit(limit)
        )

        jobs = await db_ops.read_query(query=query)

        job_list = []
        for job in jobs:
            job_dict = job.to_dict()
            if job_dict["status"] == "completed":
                job_dict["download_available"] = Path(
                    job_dict["converted_filepath"]
                ).exists()
            else:
                job_dict["download_available"] = False
            job_list.append(job_dict)

        return job_list

    except Exception as e:
        logger.error(f"Error getting user OCR jobs: {e}")
        return []


async def cleanup_expired_files():
    """
    Clean up expired OCR files based on cleanup_after timestamp.
    This should be called periodically (e.g., via a scheduled task).
    """
    try:
        current_time = datetime.utcnow()
        query = Select(OCRJob).where(OCRJob.cleanup_after <= current_time)

        expired_jobs = await db_ops.read_query(query=query)

        cleaned_count = 0
        for job in expired_jobs:
            try:
                # Remove original file
                original_path = Path(job.original_filepath)
                if original_path.exists():
                    original_path.unlink()
                    logger.debug(f"Deleted original file: {original_path}")

                # Remove converted file
                converted_path = Path(job.converted_filepath)
                if converted_path.exists():
                    converted_path.unlink()
                    logger.debug(f"Deleted converted file: {converted_path}")

                # Delete job record
                await db_ops.delete_one(table=OCRJob, record_id=job.pkid)
                cleaned_count += 1

            except Exception as e:
                logger.error(f"Error cleaning up job {job.job_id}: {e}")

        logger.info(f"Cleaned up {cleaned_count} expired OCR jobs")
        return cleaned_count

    except Exception as e:
        logger.error(f"Error during OCR cleanup: {e}")
        return 0


def validate_pdf_file(file_content: bytes) -> bool:
    """
    Basic validation to check if file is a PDF.

    Args:
        file_content: File content as bytes

    Returns:
        bool: True if valid PDF, False otherwise
    """
    # Check PDF magic number
    return file_content.startswith(b"%PDF-")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        str: Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
