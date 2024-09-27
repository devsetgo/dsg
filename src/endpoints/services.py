
# from pytz import timezone, UTC
from fastapi import APIRouter, Query
from fastapi.responses import ORJSONResponse
from loguru import logger
from sqlalchemy import Select, asc

from ..db_tables import Categories
from ..resources import db_ops

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
