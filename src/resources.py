# -*- coding: utf-8 -*-
"""
This module, `resources.py`, is responsible for setting up and managing resources for the application.

It includes the following functionalities:

1. Setting up CSRF protection using the `CsrfProtect` class from the `fastapi_csrf_protect` package.
2. Setting up templates and static files using the `Jinja2Templates` and `StaticFiles` classes from the `fastapi` package.
3. Setting up database operations using the `DatabaseOperations` class from the `dsg_lib` package.
4. Defining startup and shutdown routines for the application.
5. Adding system data to the database with `add_system_data` function, which includes adding an admin user, a default user, categories, and interesting things.

Each function in the module includes its own docstring explaining what it does.

Example:
    from resources import get_csrf_config, templates, statics, db_ops

This module uses the `loguru` library for logging and the `pydantic` library for data validation and settings management.
"""
import random
import secrets
from datetime import datetime, timedelta

import silly
from dsg_lib.async_database_functions import database_operations
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import Select, func
from tqdm import tqdm

from .db_init import async_db
from .db_tables import Categories, InterestingThings, Notes, User
from .functions.hash_function import hash_password
from .settings import settings


class CsrfSettings(BaseModel):
    """
    This class is a Pydantic model for CSRF settings.

    It includes the following fields:
    - secret_key: The secret key used for CSRF protection. It's generated using the secrets.token_hex function.
    - cookie_samesite: The 'SameSite' attribute for the CSRF cookie. It's set to 'none' by default.
    - cookie_secure: A boolean indicating whether the CSRF cookie should be secure. It's set to True by default.
    - token_location: The location of the CSRF token in the request. It's set to 'body' by default.
    - token_key: The key of the CSRF token in the request. It's set to 'csrf-token' by default.

    This class is used by the `get_csrf_config` function to load the CSRF settings.
    """

    secret_key: str = secrets.token_hex(
        128
    )  # Generate a 128-byte secret key for CSRF protection
    cookie_samesite: str = (
        "none"  # Set the 'SameSite' attribute for the CSRF cookie to 'none'
    )
    cookie_secure: bool = True  # Set the CSRF cookie to be secure
    token_location: str = (
        "body"  # Set the location of the CSRF token in the request to 'body'
    )
    token_key: str = (
        "csrf-token"  # Set the key of the CSRF token in the request to 'csrf-token'
    )


@CsrfProtect.load_config
def get_csrf_config():
    """
    This function is used to load the CSRF settings for the application.

    It's decorated with the `@CsrfProtect.load_config` decorator, which tells the `CsrfProtect` class to use this function to load the CSRF settings.

    The function creates an instance of the `CsrfSettings` class, which is a Pydantic model that defines the CSRF settings. The `CsrfSettings` class includes fields for the secret key, the 'SameSite' attribute for the CSRF cookie, whether the CSRF cookie should be secure, the location of the CSRF token in the request, and the key of the CSRF token in the request.

    Returns:
        CsrfSettings: An instance of the `CsrfSettings` class with the CSRF settings for the application.
    """
    return (
        CsrfSettings()
    )  # Return an instance of the `CsrfSettings` class with the CSRF settings


# templates and static files
templates = Jinja2Templates(directory="templates")
statics = StaticFiles(directory="static")

logger.info("setting up database operations")
db_ops = database_operations.DatabaseOperations(async_db)
logger.info("database setup complete")


async def startup():
    """
    This function is used to start up the application.

    It's an asynchronous function, which means it can be used with the `await` keyword.

    The function does the following:
    - Logs that the services are starting up.
    - Checks the database for tables.
    - Creates the database tables if they don't exist.
    - Logs the names of the tables that have been created.
    - Adds system data to the database.

    This function is typically called when the application starts up.
    """
    logger.info("starting up services")  # Log that the services are starting up

    # Create a DBConfig instance
    logger.info(
        "checking database for tables"
    )  # Log that the database is being checked for tables
    tables = (
        await db_ops.get_table_names()
    )  # Get the names of the tables in the database

    logger.info(
        "creating database tables"
    )  # Log that the database tables are being created
    await async_db.create_tables()  # Create the database tables
    logger.info(
        "database tables created"
    )  # Log that the database tables have been created
    tables = (
        await db_ops.get_table_names()
    )  # Get the names of the tables in the database
    logger.info(
        f"tables {tables} have been created"
    )  # Log the names of the tables that have been created
    await add_system_data()  # Add system data to the database


async def shutdown():
    # This function is used to shut down the application.
    # It's an asynchronous function, which means it can be used with the `await` keyword.
    # The function does the following:
    # - Logs that the services are shutting down.
    # - Disconnects from the database.
    # This function is typically called when the application is shutting down.

    logger.info("shutting down services")  # Log that the services are shutting down

    # Disconnect from the database
    logger.info(
        "disconnecting from database"
    )  # Log that the application is disconnecting from the database


async def add_system_data():
    # This function is responsible for adding system data to the application.
    # It checks various settings and based on those settings, it creates an admin user, a demo user, base categories, and demo data.

    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        data = await add_admin()  # Create an admin user
        if settings.create_demo_data is True:
            await add_notes(user_id=data)  # Create notes for the admin user

    if settings.create_demo_user is True:
        logger.warning("Creating demo user")
        await add_user()  # Create a demo user

    if settings.create_base_categories is True:
        logger.warning("Creating base categories")
        await add_categories()  # Create base categories

    if settings.create_demo_data is True:
        logger.warning("Creating demo data")
        await add_interesting_things()  # Create demo data


async def add_admin():
    # This function is responsible for creating an admin user.
    # It creates a User instance with the admin user details and then tries to add it to the database.
    # If the user is successfully added, it logs the full name of the user.
    # If there's an error while adding the user, it logs the error.

    if settings.create_admin_user is True:
        logger.warning("creating admin user")
        user_name = settings.admin_user.get_secret_value()
        password = settings.admin_password.get_secret_value()

        hashed_password = hash_password(password)
        user = User(
            first_name="Admin",
            last_name="User",
            user_name=user_name,
            password=hashed_password,
            is_active=True,
            is_admin=True,
        )
        try:
            await db_ops.create_one(user)
            user = await db_ops.read_one_record(
                Select(User).where(User.user_name == user_name)
            )
            # print the full_name property
            logger.warning(f"Admin created: {user.full_name}")
            return user.pkid
        except Exception as e:
            logger.error(e)


async def add_notes(user_id: str, qty_notes: int = settings.create_demo_notes_qty):
    moods = ["positive", "neutral", "negative"]
    demo_notes = []

    for _ in tqdm(range(qty_notes)):

        mood = random.choice(moods)
        mood_analysis = random.choice(moods)
        length = random.randint(1, 20)
        note = silly.paragraph(length=length)
        summary = note[:50]
        tags = list(set([silly.adjective() for x in range(1, 4)]))

        # Generate a random date within the last X years
        days_in_three_years = 365 * 5
        random_number_of_days = random.randrange(days_in_three_years)
        date_created = datetime.now() - timedelta(days=random_number_of_days)

        # Make date_updated the same as date_created or 3-15 days later
        days_to_add = random.choice([0] + list(range(3, 16)))
        date_updated = date_created + timedelta(days=days_to_add)

        # Create the note
        note = Notes(
            mood=mood,
            note=note,
            summary=summary,
            tags=tags,
            mood_analysis=mood_analysis,
            user_id=user_id,
            date_created=date_created,
            date_updated=date_updated,
        )
        demo_notes.append(note)
        # data = await db_ops.create_one(note)
    data = await db_ops.create_many(demo_notes)


async def add_user():
    # This function is responsible for adding a default user 'Mike' as a system admin.
    # It first checks if the user 'Mike' already exists in the database.
    # If the user exists, it logs that the system user has already been added and returns.
    # If the user doesn't exist, it creates a User instance with the user details and then tries to add it to the database.
    # If the user is successfully added, it logs the full name of the user.
    # If there's an error while adding the user, it logs the error.

    user = await db_ops.read_query(Select(User).where(User.user_name == "Mike"))
    if len(user) > 0:
        logger.info("system user already added")
        return

    logger.info("adding system user")
    hashed_password = hash_password("password")
    user = User(
        first_name="Mike",
        last_name="Ryan",
        user_name="Mike",
        password=hashed_password,
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

    except Exception as e:
        logger.error(e)


async def add_categories():
    # This function is responsible for adding system categories.
    # It first checks if any categories already exist in the database.
    # If categories exist, it logs that the system categories have already been added and returns.
    # If no categories exist, it creates a Categories instance for each category in the list and then tries to add it to the database.
    # If there's an error while adding a category, it logs the error.
    # After all categories have been added, it logs the name of each category.

    # cat_number = await db_ops.count_query(Categories)
    # Query the User table and count the number of categories for each user
    cat_number = await db_ops.count_query(query=Select(func.count(Categories.pkid)))

    if cat_number == 0:
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
        logger.info(f"category name: {d.name}")


async def add_interesting_things():
    # This function is responsible for adding a list of interesting things to the database.
    # Each item in the list is a dictionary with keys for name, description, url, and category.

    # Define the list of items to be added
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
    # Check to see if the items are already in the database
    for item in my_stuff:
        # Query the database for each item by name
        data = await db_ops.read_query(
            Select(InterestingThings).where(InterestingThings.name == item["name"])
        )
        # If the item already exists in the database, log a message and return
        if len(data) > 0:
            logger.info(f"system item {item['name']} already added")
            return

    # Get the user record for 'Mike'
    user = await db_ops.read_one_record(Select(User).where(User.user_name == "Mike"))

    # Loop through the list of items
    for item in my_stuff:
        # Get the category record for the current item
        category = await db_ops.read_one_record(
            Select(Categories).where(Categories.name == str(item["category"]).title())
        )
        # Log the category name
        logger.info(category.name)
        # Log a message indicating that the current item is being added
        logger.info(f"adding system item {item['name']}")
        # Create a new InterestingThings instance with the item details
        thing = InterestingThings(
            name=item["name"],
            description=item["description"],
            url=item["url"],
            user_id=user.pkid,
            category=category.name,
        )
        # Try to add the new item to the database
        try:
            await db_ops.create_one(thing)
        except Exception as e:
            # If there's an error while adding the item, log the error
            logger.error(e)

    # Get all items from the InterestingThings table
    all_things = await db_ops.read_query(Select(InterestingThings))
    # Log the name, category, URL, and description of each item
    for thing in all_things:
        logger.info(f"{thing.name}, {thing.category}, {thing.url}, {thing.description}")
