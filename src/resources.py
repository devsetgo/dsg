# -*- coding: utf-8 -*-
from loguru import logger
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import settings
from com_lib import db_setup


from com_lib.db_setup import create_db
from com_lib.demo_data import make_a_lot_of_calls
from endpoints.main.crud import get_data

# templates and static files
templates = Jinja2Templates(directory="templates")
statics = StaticFiles(directory="static")


async def startup():

    logger.info("starting up services")
    await db_setup.connect_db()
    logger.info("connecting to database")

async def shutdown():

    logger.info("shutting down services")
    await db_setup.disconnect_db()
    logger.info("disconnecting from database")


def init_app():

    # config_log()
    # logger.info("Initiating application")
    create_db()
    logger.info("Initiating database")

