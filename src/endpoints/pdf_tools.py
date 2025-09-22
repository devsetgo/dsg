# -*- coding: utf-8 -*-
"""
PDF Tools Endpoints

This module provides API endpoints for PDF processing tools, including OCR conversion.
It handles PDF file uploads, OCR processing, and file downloads with automatic cleanup.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - FastAPI: For API endpoints
    - pathlib: For file path operations
    - loguru: For logging
    - sqlalchemy: For database operations
"""

import os
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter, 
    BackgroundTasks, 
    Depends, 
    File, 
    HTTPException, 
    Path as FastAPIPath,
    Query,
    Request, 
    Response, 
    UploadFile,
    status
)
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, HTMLResponse
from loguru import logger
from sqlalchemy import Select

from ..db_tables import OCRJob, Requirement
from ..functions.login_required import check_login
from ..functions.ocr_processing import (
    cleanup_expired_files,
    format_file_size,
    get_ocr_job_status,
    get_user_ocr_jobs,
    process_ocr_pdf,
    save_uploaded_pdf,
    validate_pdf_file
)
from ..functions.pypi_core import check_packages
from ..functions.pypi_metrics import get_pypi_metrics
from ..resources import db_ops, templates

router = APIRouter()


# OCR Endpoints
@router.get("/ocr", response_class=HTMLResponse)
async def ocr_dashboard(request: Request):
    """Display OCR dashboard with metrics and role-based access"""
    user_info = await check_login(request)
    
    from ..functions.ocr_metrics import get_ocr_metrics, get_user_ocr_summary, get_recent_ocr_jobs
    
    context = {
        "page": "pdf_tools",
        "request": request,
        "user_info": user_info
    }
    
    # If admin, get system-wide metrics and recent jobs
    if user_info.get("is_admin"):
        try:
            context["ocr_metrics"] = await get_ocr_metrics()
            context["recent_jobs"] = await get_recent_ocr_jobs(limit=20)
        except Exception as e:
            logger.error(f"Error getting admin OCR metrics: {e}")
            context["ocr_metrics"] = {}
            context["recent_jobs"] = []
    else:
        # For regular users, get their personal summary
        try:
            user_id = user_info["user_identifier"]
            context["user_summary"] = await get_user_ocr_summary(user_id)
        except Exception as e:
            logger.error(f"Error getting user OCR summary: {e}")
            context["user_summary"] = {}
    
    return templates.TemplateResponse("pdf_tools/ocr_dashboard.html", context)


@router.post("/ocr/upload")
async def upload_pdf_for_ocr(
    background_tasks: BackgroundTasks,
    request: Request,
    pdf_file: UploadFile = File(...),
    user_info: dict = Depends(check_login),
):
    """Upload a PDF file for OCR processing."""
    user_id = user_info["user_identifier"]
    
    try:
        # Validate file
        if not pdf_file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No filename provided"
            )
            
        if not pdf_file.filename.lower().endswith('.pdf'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are allowed"
            )
        
        # Check file size (limit to 50MB)
        content = await pdf_file.read()
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 50MB limit"
            )
            
        # Reset file pointer and validate PDF content
        await pdf_file.seek(0)
        if not validate_pdf_file(content):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid PDF file"
            )
            
        # Reset file pointer for processing
        await pdf_file.seek(0)
        
        # Save uploaded file and create job record
        job_info = await save_uploaded_pdf(pdf_file, user_id)
        
        # Add OCR processing to background tasks
        background_tasks.add_task(process_ocr_pdf, job_info["job_id"])
        
        logger.info(f"PDF upload successful for user {user_id}, job {job_info['job_id']}")
        
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": "PDF uploaded successfully. Processing started.",
                "job_id": job_info["job_id"],
                "original_filename": job_info["original_filename"],
                "file_size": format_file_size(job_info["file_size"])
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading PDF for OCR: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process PDF upload"
        )


@router.post("/ocr/status", response_class=HTMLResponse)
async def check_ocr_status_form(request: Request):
    """Handle form-based OCR status check from dashboard"""
    try:
        form_data = await request.form()
        job_id = form_data.get("job_id")
        
        if not job_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job ID is required"
            )
        
        # Get job from database (public access for status check)
        query = Select(OCRJob).where(OCRJob.job_id == job_id)
        job = await db_ops.read_one_record(query=query)
        
        if not job:
            context = {
                "request": request,
                "error": "Job not found. Please check your Job ID.",
                "job_id": job_id
            }
            return templates.TemplateResponse("ocr_status.html", context)
        
        # Format job information for template
        job_info = {
            "job_id": job.job_id,
            "original_filename": job.original_filename,
            "status": job.status,
            "date_created": job.date_created,
            "date_completed": job.date_completed,
            "page_count": job.page_count,
            "file_size_original": format_file_size(job.file_size_original) if job.file_size_original else None,
            "file_size_converted": format_file_size(job.file_size_converted) if job.file_size_converted else None,
            "processing_time": job.processing_time,
            "error_message": job.error_message,
            "can_download": job.status == "completed" and Path(job.converted_filepath or "").exists()
        }
        
        context = {
            "request": request,
            "job": job_info,
            "job_id": job_id
        }
        
        return templates.TemplateResponse("ocr_status.html", context)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in form-based status check: {e}")
        context = {
            "request": request,
            "error": "Unable to check job status. Please try again.",
            "job_id": form_data.get("job_id", "") if "form_data" in locals() else ""
        }
        return templates.TemplateResponse("ocr_status.html", context)


@router.get("/ocr/download/{job_id}")
async def download_pdf_public(job_id: str = FastAPIPath(..., description="OCR job ID")):
    """Public download endpoint for completed OCR jobs (no authentication required)"""
    try:
        # Get job from database
        query = Select(OCRJob).where(OCRJob.job_id == job_id)
        job = await db_ops.read_one_record(query=query)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="OCR job not found"
            )
            
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR processing not completed yet"
            )
            
        converted_filepath = Path(job.converted_filepath or "")
        if not converted_filepath.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Converted file not found (may have been cleaned up)"
            )
            
        # Generate download filename
        original_filename = job.original_filename
        name_without_ext = Path(original_filename).stem
        download_filename = f"{name_without_ext}_ocr_converted.pdf"
        
        logger.info(f"Public download of OCR job {job_id}: {download_filename}")
        
        return FileResponse(
            path=converted_filepath,
            filename=download_filename,
            media_type="application/pdf"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in public download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file"
        )
