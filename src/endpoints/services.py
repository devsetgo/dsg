from datetime import datetime

# from pytz import timezone, UTC
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query, Request
from fastapi.responses import JSONResponse, ORJSONResponse, RedirectResponse
from loguru import logger
from sqlalchemy import Select, Text, and_, asc, cast, or_

from ..db_tables import Categories, Posts, Users
from ..functions import ai, date_functions
from ..functions.login_required import check_login
from ..resources import db_ops, templates

router = APIRouter()

cat_list = ["is_post", "is_weblink", "is_system"]


@router.get("/categories", response_class=ORJSONResponse)
async def get_categories(category_name: str = Query(None, enum=cat_list)):
    try:
        if category_name is None:
            categories = await db_ops.read_query(
                Select(Categories).order_by(asc(Categories.name))
            )
        else:
            categories = await db_ops.read_query(
                Select(Categories)
                .where(getattr(Categories, category_name) == True)
                .order_by(asc(Categories.name))
            )

        cat_list = [cat.to_dict()["name"] for cat in categories]
        return cat_list
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return []
