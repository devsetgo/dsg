# -*- coding: utf-8 -*-
import secrets

from dsg_lib import database_operations
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Select

from .db_init import async_db
from .db_tables import Categories, InterestingThings, User


class CsrfSettings(BaseModel):
    secret_key: str = secrets.token_hex(128)
    cookie_samesite: str = "none"
    cookie_secure: bool = True
    token_location: str = "body"
    token_key: str = "csrf-token"


@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()


# templates and static files
templates = Jinja2Templates(directory="templates")
statics = StaticFiles(directory="static")

logger.info("setting up database operations")
db_ops = database_operations.DatabaseOperations(async_db)
logger.info("database setup complete")


async def startup():
    print("startup")
    logger.info("starting up services")

    # Create a DBConfig instance
    logger.info("checking database for tables")
    tables = await db_ops.get_table_names()
    print(tables)
    # if len(tables) > 0: logger.info("database already created") else:
    print("creating tables")
    logger.info("creating database tables")
    await async_db.create_tables()
    logger.info("database tables created")
    tables = await db_ops.get_table_names()
    logger.info(f"tables {tables} have been created")
    await add_system_data()


async def shutdown():
    logger.info("shutting down services")

    logger.info("disconnecting from database")


def init_app():
    logger.info("Initiating database")


async def add_system_data():
    await add_user()
    await add_categories()
    await add_interesting_things()


async def add_user():
    # add a default user 'Mike' as a system admin
    user = await db_ops.read_query(Select(User).where(User.user_name == "Mike"))
    if len(user) > 0:
        logger.info("system user already added")
        return

    logger.info("adding system user")
    user = User(
        first_name="Mike",
        last_name="Ryan",
        user_name="Mike",
        password="password",
        is_active=True,
        is_admin=True,
    )
    try:
        await db_ops.create_one(user)
        user = await db_ops.read_one_record(
            Select(User).where(User.user_name == "Mike")
        )
        # print the full_name property
        logger.info(user.full_name)
        print(user.full_name)
    except Exception as e:
        logger.error(e)


async def add_categories():
    cat_number = await db_ops.count_query(Categories)

    if cat_number > 0:
        logger.info("system categories already added")
        return

    cat: list = ["technology", "news", "sites", "programming", "woodworking", "other"]

    user = await db_ops.read_one_record(Select(User).where(User.user_name == "Mike"))

    for c in cat:
        logger.info(f"adding system category {c}")
        category = Categories(
            name=c.title(),
            description=f"{str(c).title()} related items",
            is_system=True,
            is_active=True,
            user_id=user.pkid,
        )
        try:
            await db_ops.create_one(category)
        except Exception as e:
            logger.error(e)
    data = await db_ops.read_query(Select(Categories))

    for d in data:
        print(d.name)


async def add_interesting_things():
    my_stuff = [
        {
            "name": "Test API",
            "description": "An example API built with FastAPI",
            "url": "https://test-api.devsetgo.com/",
            "category": "programming",
        },
        {
            "name": "Starlette Dashboard",
            "description": "A Starlette based version of the AdminLTE template.",
            "url": "https://stardash.devsetgo.com/",
            "category": "programming",
        },
        {
            "name": "DevSetGo Library",
            "description": "A helper library I use for my Python projects",
            "url": "https://devsetgo.github.io/devsetgo_lib/",
            "category": "programming",
        },
        {
            "name": "Pypi Checker",
            "description": "Get the latest version of python libraries",
            "url": "/pypi",
            "category": "programming",
        },
        {
            "name": "FastAPI",
            "description": "An async Python framework for building great APIs",
            "category": "programming",
            "url": "https://fastapi.tiangolo.com/",
        },
        {
            "name": "Starlette",
            "description": "An async Python framework for building sites and is what\
                 FastAPI is built on top of.",
            "category": "programming",
            "url": "https://fastapi.tiangolo.com/",
        },
        {
            "name": "Portainer",
            "description": "How to manage containers for Docker or Kubernetes",
            "url": "https://www.portainer.io/",
            "category": "technology",
        },
        {
            "name": "Digital Ocean",
            "description": "Great hosting option for servers, apps, and K8s. Plus great\
                 documentation and tutorials. (referral link) ",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "technology",
        },
        {
            "name": "Kubernetes",
            "description": "Run containers at scale.",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "programming",
        },
    ]
    # check to see if the items are already in the database
    for item in my_stuff:
        data = await db_ops.read_query(
            Select(InterestingThings).where(InterestingThings.name == item["name"])
        )
        if len(data) > 0:
            logger.info(f"system item {item['name']} already added")
            return

    # add my stuff to the database in the InterestingThings table when looping
    # through the list of items, we need to get the user_id and category_id to
    # add to the database
    user = await db_ops.read_one_record(Select(User).where(User.user_name == "Mike"))

    for item in my_stuff:
        category = await db_ops.read_one_record(
            Select(Categories).where(Categories.name == str(item["category"]).title())
        )
        print(category.name)
        logger.info(f"adding system item {item['name']}")
        thing = InterestingThings(
            name=item["name"],
            description=item["description"],
            url=item["url"],
            user_id=user.pkid,
            category=category.name,
        )
        try:
            await db_ops.create_one(thing)
        except Exception as e:
            logger.error(e)
    all_things = await db_ops.read_query(Select(InterestingThings))
    for thing in all_things:
        print(thing.name, thing.category, thing.url, thing.description)
