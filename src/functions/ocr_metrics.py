# -*- coding: utf-8 -*-
"""
OCR Metrics Module

This module provides comprehensive metrics for the OCR system, including
job counts, processing statistics, user metrics, and system performance data.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List

from loguru import logger
from sqlalchemy import Select, func, and_

from ..db_tables import OCRJob
from ..resources import db_ops


async def get_ocr_metrics():
    """Get comprehensive OCR system metrics"""
    # Basic job counts
    try:
        total_jobs = await db_ops.count_query(query=Select(OCRJob)) or 0
    except Exception as e:
        logger.error(f"Error getting total OCR jobs: {e}")
        total_jobs = 0

    try:
        completed_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(OCRJob.status == "completed")
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting completed OCR jobs: {e}")
        completed_jobs = 0

    try:
        failed_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(OCRJob.status == "failed")
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting failed OCR jobs: {e}")
        failed_jobs = 0

    try:
        processing_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(OCRJob.status == "processing")
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting processing OCR jobs: {e}")
        processing_jobs = 0

    try:
        unique_users = (
            await db_ops.count_query(query=Select(OCRJob.user_id).distinct()) or 0
        )
    except Exception as e:
        logger.error(f"Error getting unique OCR users: {e}")
        unique_users = 0

    try:
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(OCRJob.date_created >= yesterday)
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting recent OCR jobs: {e}")
        recent_jobs = 0

    # Get detailed metrics from completed jobs
    total_pages = 0
    total_size_original = 0
    total_size_converted = 0
    avg_processing_time = 0.0

    try:
        completed_job_records = await db_ops.read_query(
            query=Select(OCRJob).where(OCRJob.status == "completed")
        )

        if completed_job_records and isinstance(completed_job_records, list):
            # Calculate totals using safe attribute access
            total_pages = sum(
                getattr(job, "page_count", 0) or 0 for job in completed_job_records
            )
            total_size_original = sum(
                getattr(job, "file_size_original", 0) or 0
                for job in completed_job_records
            )
            total_size_converted = sum(
                getattr(job, "file_size_converted", 0) or 0
                for job in completed_job_records
            )

            # Calculate average processing time
            processing_times = [
                getattr(job, "processing_time", 0) or 0
                for job in completed_job_records
                if getattr(job, "processing_time", None) is not None
            ]

            if processing_times:
                avg_processing_time = round(
                    sum(processing_times) / len(processing_times), 2
                )

    except Exception as e:
        logger.error(f"Error calculating detailed metrics: {e}")

    # Calculate derived metrics
    success_rate = 0.0
    if total_jobs > 0:
        success_rate = round((completed_jobs / total_jobs) * 100, 1)

    space_savings = 0.0
    if total_size_original > 0 and total_size_converted > 0:
        space_savings = round(
            ((total_size_original - total_size_converted) / total_size_original) * 100,
            1,
        )

    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "processing_jobs": processing_jobs,
        "unique_users": unique_users,
        "total_pages": total_pages,
        "total_size_original": total_size_original,
        "total_size_converted": total_size_converted,
        "recent_jobs": recent_jobs,
        "avg_processing_time": avg_processing_time,
        "success_rate": success_rate,
        "space_savings": space_savings,
    }


async def get_user_ocr_summary(user_id: str) -> Dict[str, Any]:
    """Get OCR metrics for a specific user"""
    try:
        user_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(OCRJob.user_id == user_id)
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting user jobs count: {e}")
        user_jobs = 0

    try:
        user_completed_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(
                    and_(OCRJob.user_id == user_id, OCRJob.status == "completed")
                )
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting user completed jobs: {e}")
        user_completed_jobs = 0

    try:
        user_failed_jobs = (
            await db_ops.count_query(
                query=Select(OCRJob).where(
                    and_(OCRJob.user_id == user_id, OCRJob.status == "failed")
                )
            )
            or 0
        )
    except Exception as e:
        logger.error(f"Error getting user failed jobs: {e}")
        user_failed_jobs = 0

    # Get user's recent jobs (last 10)
    user_recent_jobs = []
    try:
        user_recent_jobs_records = await db_ops.read_query(
            query=Select(OCRJob)
            .where(OCRJob.user_id == user_id)
            .order_by(OCRJob.date_created.desc())
            .limit(10)
        )

        if user_recent_jobs_records and isinstance(user_recent_jobs_records, list):
            user_recent_jobs = [
                {
                    "job_id": getattr(job, "job_id", ""),
                    "original_filename": getattr(job, "original_filename", ""),
                    "status": getattr(job, "status", ""),
                    "date_created": getattr(job, "date_created", None),
                    "page_count": getattr(job, "page_count", 0),
                    "processing_time": getattr(job, "processing_time", 0),
                }
                for job in user_recent_jobs_records
            ]
    except Exception as e:
        logger.error(f"Error getting user recent jobs: {e}")

    # Calculate user success rate
    user_success_rate = 0.0
    if user_jobs > 0:
        user_success_rate = round((user_completed_jobs / user_jobs) * 100, 1)

    return {
        "user_jobs": user_jobs,
        "user_completed_jobs": user_completed_jobs,
        "user_failed_jobs": user_failed_jobs,
        "user_success_rate": user_success_rate,
        "user_recent_jobs": user_recent_jobs,
    }


async def get_recent_ocr_jobs(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent OCR jobs for admin dashboard"""
    try:
        recent_jobs_records = await db_ops.read_query(
            query=Select(OCRJob).order_by(OCRJob.date_created.desc()).limit(limit)
        )

        if recent_jobs_records and isinstance(recent_jobs_records, list):
            return [
                {
                    "job_id": getattr(job, "job_id", ""),
                    "user_id": getattr(job, "user_id", ""),
                    "original_filename": getattr(job, "original_filename", ""),
                    "status": getattr(job, "status", ""),
                    "date_created": getattr(job, "date_created", None),
                    "date_completed": getattr(job, "date_completed", None),
                    "page_count": getattr(job, "page_count", 0),
                    "file_size_original": getattr(job, "file_size_original", 0),
                    "processing_time": getattr(job, "processing_time", 0),
                }
                for job in recent_jobs_records
            ]
    except Exception as e:
        logger.error(f"Error getting recent OCR jobs: {e}")

    return []


from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy import Select, func, and_

from ..db_tables import OCRJob, Users
from ..resources import db_ops


async def get_ocr_metrics():
    """Get comprehensive OCR system metrics"""
    try:
        # Total OCR jobs count
        total_jobs = await db_ops.count_query(query=Select(OCRJob))
    except Exception as e:
        logger.error(f"Error getting total OCR jobs: {e}")
        total_jobs = 0

    try:
        # Completed jobs count
        completed_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(OCRJob.status == "completed")
        )
    except Exception as e:
        logger.error(f"Error getting completed OCR jobs: {e}")
        completed_jobs = 0

    try:
        # Failed jobs count
        failed_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(OCRJob.status == "failed")
        )
    except Exception as e:
        logger.error(f"Error getting failed OCR jobs: {e}")
        failed_jobs = 0

    try:
        # Processing jobs count
        processing_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(OCRJob.status == "processing")
        )
    except Exception as e:
        logger.error(f"Error getting processing OCR jobs: {e}")
        processing_jobs = 0

    try:
        # Unique users who have used OCR
        unique_users = await db_ops.count_query(query=Select(OCRJob.user_id).distinct())
    except Exception as e:
        logger.error(f"Error getting unique OCR users: {e}")
        unique_users = 0

    try:
        # Total pages processed (sum of page counts)
        total_pages = await db_ops.count_query(
            query=Select(func.sum(OCRJob.page_count)).where(
                OCRJob.status == "completed"
            )
        )
        total_pages = total_pages or 0
    except Exception as e:
        logger.error(f"Error getting total pages processed: {e}")
        total_pages = 0

    try:
        # Total file size processed (original files)
        total_size_original = await db_ops.count_query(
            query=Select(func.sum(OCRJob.file_size_original)).where(
                OCRJob.status == "completed"
            )
        )
        total_size_original = total_size_original or 0
    except Exception as e:
        logger.error(f"Error getting total original file size: {e}")
        total_size_original = 0

    try:
        # Total file size after conversion
        total_size_converted = await db_ops.count_query(
            query=Select(func.sum(OCRJob.file_size_converted)).where(
                OCRJob.status == "completed"
            )
        )
        total_size_converted = total_size_converted or 0
    except Exception as e:
        logger.error(f"Error getting total converted file size: {e}")
        total_size_converted = 0

    try:
        # Jobs in last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(OCRJob.date_created >= yesterday)
        )
    except Exception as e:
        logger.error(f"Error getting recent OCR jobs: {e}")
        recent_jobs = 0

    try:
        # Average processing time - using simplified approach
        completed_job_records = await db_ops.read_query(
            query=Select(OCRJob).where(OCRJob.status == "completed")
        )
        processing_times = []
        for job in completed_job_records:
            if job.processing_time is not None:
                processing_times.append(job.processing_time)

        avg_processing_time = (
            round(sum(processing_times) / len(processing_times), 2)
            if processing_times
            else 0.0
        )
    except Exception as e:
        logger.error(f"Error getting average processing time: {e}")
        avg_processing_time = 0.0

    # Calculate success rate
    success_rate = 0
    if total_jobs > 0:
        success_rate = round((completed_jobs / total_jobs) * 100, 1)

    # Calculate space savings (compression ratio)
    space_savings = 0
    if total_size_original > 0 and total_size_converted > 0:
        space_savings = round(
            ((total_size_original - total_size_converted) / total_size_original) * 100,
            1,
        )

    return {
        "total_jobs": total_jobs,
        "completed_jobs": completed_jobs,
        "failed_jobs": failed_jobs,
        "processing_jobs": processing_jobs,
        "unique_users": unique_users,
        "total_pages": total_pages,
        "total_size_original": total_size_original,
        "total_size_converted": total_size_converted,
        "recent_jobs": recent_jobs,
        "avg_processing_time": avg_processing_time,
        "success_rate": success_rate,
        "space_savings": space_savings,
    }


async def get_user_ocr_summary(user_id: str):
    """Get OCR summary for a specific user"""
    try:
        # User's total jobs
        user_total_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(OCRJob.user_id == user_id)
        )

        # User's completed jobs
        user_completed_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(
                and_(OCRJob.user_id == user_id, OCRJob.status == "completed")
            )
        )

        # User's failed jobs
        user_failed_jobs = await db_ops.count_query(
            query=Select(OCRJob).where(
                and_(OCRJob.user_id == user_id, OCRJob.status == "failed")
            )
        )

        # User's total pages processed
        result = await db_ops.get_one_query(
            query=Select(func.sum(OCRJob.page_count)).where(
                and_(OCRJob.user_id == user_id, OCRJob.status == "completed")
            )
        )
        user_total_pages = result[0] if result and result[0] else 0

        return {
            "user_total_jobs": user_total_jobs,
            "user_completed_jobs": user_completed_jobs,
            "user_failed_jobs": user_failed_jobs,
            "user_total_pages": user_total_pages,
        }

    except Exception as e:
        logger.error(f"Error getting user OCR summary: {e}")
        return {
            "user_total_jobs": 0,
            "user_completed_jobs": 0,
            "user_failed_jobs": 0,
            "user_total_pages": 0,
        }
