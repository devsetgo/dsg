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


my_stuff = [
    {
        "name": "Test API",
        "description": "An example API built with FastAPI",
        "url": "https://test-api.devsetgo.com/",
        "tags": ["Python", "Async", "OpenAPI", "Framework"],
    },
    {
        "name": "Starlette Dashboard",
        "description": "A Starlette based version of the AdminLTE template.",
        "url": "https://stardash.devsetgo.com/",
        "tags": ["Python", "Async", "Framework", "Dashboard", "Admin"],
    },
    {
        "name": "DevSetGo Library",
        "description": "A helper library I use for my Python projects",
        "url": "https://devsetgo.github.io/devsetgo_lib/",
        "tags": ["Python", "Logging", "CSV", "JSON"],
    },
    {
        "name": "Pypi Checker",
        "description": "Get the latest version of python libraries",
        "url": "/pypi",
        "tags": ["Python", "PyPi", "library", "update"],
    },
]
cool_stuff = [
    {
        "name": "FastAPI",
        "description": "An async Python framework for building great APIs",
        "tags": ["Python", "Async", "OpenAPI"],
        "url": "https://fastapi.tiangolo.com/",
    },
    {
        "name": "Starlette",
        "description": "An async Python framework for building sites and is what FastAPI is built on top of.",
        "tags": ["Python", "Async", "OpenAPI"],
        "url": "https://fastapi.tiangolo.com/",
    },
    {
        "name": "Portainer",
        "description": "How to manage containers for Docker or Kubernetes",
        "url": "https://www.portainer.io/",
    },
    {
        "name": "Digital Ocean",
        "description": "Great hosting option for servers, apps, and K8s. Plus great documentation and tutorials. (referral link) ",
        "url": "https://m.do.co/c/9a3b3c4fbc90",
    },
    {
        "name": "Kubernetes",
        "description": "Run containers at scale.",
        "url": "https://m.do.co/c/9a3b3c4fbc90",
    },
]
