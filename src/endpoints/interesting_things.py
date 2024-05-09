# -*- coding: utf-8 -*-
import csv
import io
from datetime import UTC, datetime, timedelta

# from pytz import timezone, UTC
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Path,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pytz import timezone
from sqlalchemy import Select, Text, and_, between, cast, extract, or_

from ..db_tables import NoteMetrics, Notes
from ..functions import ai, date_functions, note_import, notes_metrics
from ..functions.login_required import check_login
from ..resources import db_ops, templates
from ..settings import settings

router = APIRouter()

# api endpoints
# /list with filters (by tag, by date range, by category)

# get /item/{id}

# post (edit) /item/{id}

# post (delete) /delete/{id}

# 
