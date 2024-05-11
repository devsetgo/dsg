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
from datetime import UTC, datetime, timedelta

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
from .db_tables import Categories, InterestingThings, Notes, Posts, Users
from .functions.hash_function import hash_password
from .functions.models import RoleEnum
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
    logger.info("starting up services")
    logger.info("checking database for tables")
    tables = await db_ops.get_table_names()
    logger.info("creating database tables")

    # if tables.__len__() == 0:
    await async_db.create_tables()
    logger.info("database tables created")
    tables = await db_ops.get_table_names()
    logger.info(f"tables {tables} have been created")

    user = await db_ops.read_query(Select(Users))
    if len(user) == 0:
        await add_system_data()


async def shutdown():
    """
    This function is used to shut down the application.
    It's an asynchronous function, which means it can be used with the `await` keyword.
    The function does the following:
    - Logs that the services are shutting down.
    - Disconnects from the database.
    This function is typically called when the application is shutting down.
    """

    # Log that the services are shutting down
    logger.info("shutting down services")

    # Disconnect from the database
    logger.info("disconnecting from database")


async def add_system_data():
    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        data = await add_admin()  # Create an admin user

        if settings.create_demo_notes is True:
            await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    if settings.create_demo_user == True:
        logger.warning("Creating demo user")
        for _ in range(settings.create_demo_users_qty):
            data = await add_user()  # Create a demo user
            await add_notes(
                user_id=data["pkid"], qty_notes=random.randint(1, 5)
            )  # Create notes for the loop user

    if settings.create_base_categories is True:
        logger.warning("Creating base categories")
        await add_categories()  # Create base categories

    if settings.create_demo_data is True:
        logger.warning("Creating demo data")
        await add_interesting_things()  # Create demo data
        await add_posts()


async def add_admin():
    if settings.create_admin_user is True:
        logger.warning("creating admin user")
        user_name = settings.admin_user.get_secret_value()
        password = settings.admin_password.get_secret_value()

        add_roles = {}
        for role in RoleEnum:
            add_roles[role] = True

        hashed_password = hash_password(password)
        user = Users(
            first_name="Admin",
            last_name="Users",
            user_name=user_name,
            password=hashed_password,
            is_active=True,
            is_admin=True,
            roles=add_roles,
        )
        try:
            res = await db_ops.create_one(user)
            logger.debug(f"add admin {res.to_dict()}")
            user = await db_ops.read_one_record(
                Select(Users).where(Users.user_name == user_name)
            )

            logger.warning(f"Admin created: {user.full_name}")
            return user.to_dict()
        except Exception as e:
            logger.error(e)


async def add_notes(user_id: str, qty_notes: int = settings.create_demo_notes_qty):
    moods = ["positive", "neutral", "negative"]
    demo_notes = []
    mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

    for i in tqdm(range(5), desc=f"same day notes for {user_id}"):
        mood = random.choice(moods)
        mood_analysis_choice = random.choice(mood_analysis)

        length = random.randint(5, 20)
        note = silly.paragraph(length=length)
        summary = note[:50]
        tags = list(set([silly.adjective() for x in range(1, 4)]))

        # Make date_updated the same as date_created or 3-15 days later
        date_created = datetime.now(UTC) - timedelta(days=365 * i)

        date_updated = date_created
        note = Notes(
            mood="positive",
            note=f"{user_id} This is a note that was created in the past",
            summary="Past Note",
            tags=list(set([silly.adjective() for x in range(1, 4)])),
            mood_analysis="positive",
            user_id=user_id,
            date_created=date_created,
            date_updated=date_updated,
        )
        data = await db_ops.create_one(note)

    for _ in tqdm(range(qty_notes), desc=f"creating demo notes for {user_id}"):
        mood = random.choice(moods)
        mood_analysis_choice = random.choice(mood_analysis)

        length = random.randint(5, 20)
        note = silly.paragraph(length=length)
        summary = note[:50]
        tags = list(set([silly.adjective() for x in range(1, 4)]))

        # Generate a random date within the last X years
        days_in_three_years = 365 * 12
        random_number_of_days = random.randrange(days_in_three_years)
        date_created = datetime.now(UTC) - timedelta(days=random_number_of_days)

        # Make date_updated the same as date_created or 3-15 days later
        days_to_add = random.choice([0] + list(range(3, 16)))
        date_updated = date_created + timedelta(days=days_to_add)

        # Convert the timezone-aware datetimes to timezone-naive datetimes
        date_created = date_created.replace(tzinfo=None)
        date_updated = date_updated.replace(tzinfo=None)

        # Create the note
        note = Notes(
            mood=mood,
            note=note,
            summary=summary,
            tags=tags,
            mood_analysis=mood_analysis_choice,
            user_id=user_id,
            date_created=date_created,
            date_updated=date_updated,
        )
        # demo_notes.append(note)
        data = await db_ops.create_one(note)


async def add_user():
    logger.info("adding system user")
    hashed_password = hash_password("password")
    import secrets

    user_name = f"{silly.plural()}-{silly.noun()}{secrets.token_hex(2)}".lower()
    roles = ["notes", "interesting_things", "job_applications", "developer", "posts"]
    role_data = {}

    for role in roles:
        if random.choice([True, False]):
            role_data[role] = random.choice([True, False])

    user = Users(
        first_name=f"{silly.verb()}",
        last_name=f"{silly.noun()}",
        user_name=user_name,
        password=hashed_password,
        is_active=True,
        is_admin=random.choice([True, False]),
        roles=role_data,
        is_locked=random.choice([True, False]),
        date_last_login=datetime.utcnow(),
    )
    try:
        await db_ops.create_one(user)
        user = await db_ops.read_one_record(
            Select(Users).where(Users.user_name == user_name)
        )
        logger.info(user.full_name)
        return user.to_dict()

    except Exception as e:
        logger.error(e)

    # return user.pkid


async def add_categories():
    # This function is responsible for adding system categories.
    # It first checks if any categories already exist in the database.
    # If categories exist, it logs that the system categories have already been added and returns.
    # If no categories exist, it creates a Categories instance for each category in the list and then tries to add it to the database.
    # If there's an error while adding a category, it logs the error.
    # After all categories have been added, it logs the name of each category.

    # cat_number = await db_ops.count_query(Categories)
    # Query the Users table and count the number of categories for each user
    cat_number = await db_ops.count_query(query=Select(func.count(Categories.pkid)))

    if cat_number == 0:
        logger.info("system categories already added")
        return

    cat: list = ["technology", "news", "sites", "programming", "woodworking", "other"]

    user = await db_ops.read_one_record(Select(Users).where(Users.user_name == "admin"))

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
            "title": "Test API",
            "summary": "An example API built with FastAPI",
            "url": "https://test-api.devsetgo.com/",
            "category": "programming",
        },
        {
            "title": "Starlette Dashboard",
            "summary": "A Starlette based version of the AdminLTE template.",
            "url": "https://stardash.devsetgo.com/",
            "category": "programming",
        },
        {
            "title": "DevSetGo Library",
            "summary": "A helper library I use for my Python projects",
            "url": "https://devsetgo.github.io/devsetgo_lib/",
            "category": "programming",
        },
        {
            "title": "Pypi Checker",
            "summary": "Get the latest version of python libraries",
            "url": "/pypi",
            "category": "programming",
        },
        {
            "title": "FastAPI",
            "summary": "An async Python framework for building great APIs",
            "category": "programming",
            "url": "https://fastapi.tiangolo.com/",
        },
        {
            "title": "Starlette",
            "summary": "An async Python framework for building sites and is what\
                 FastAPI is built on top of.",
            "category": "programming",
            "url": "https://fastapi.tiangolo.com/",
        },
        {
            "title": "Portainer",
            "summary": "How to manage containers for Docker or Kubernetes",
            "url": "https://www.portainer.io/",
            "category": "technology",
        },
        {
            "title": "Digital Ocean",
            "summary": "Great hosting option for servers, apps, and K8s. Plus great\
                 documentation and tutorials. (referral link) ",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "technology",
        },
        {
            "title": "Kubernetes",
            "summary": "Run containers at scale.",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "programming",
        },
    ]
    # Check to see if the items are already in the database
    for item in my_stuff:
        # Query the database for each item by name
        data = await db_ops.read_query(
            Select(InterestingThings).where(InterestingThings.title == item["title"])
        )
        # If the item already exists in the database, log a message and return
        if len(data) > 0:
            logger.info(f"system item {item['title']} already added")
            return

    # Get the user record for 'admin'
    user = await db_ops.read_one_record(Select(Users).where(Users.user_name == "admin"))

    # Loop through the list of items
    for item in my_stuff:
        # Get the category record for the current item
        category = await db_ops.read_one_record(
            Select(Categories).where(Categories.name == str(item["category"]).title())
        )
        # Log the category name
        logger.info(category.name)
        # Log a message indicating that the current item is being added
        logger.info(f"adding system item {item['title']}")
        # Create a new InterestingThings instance with the item details
        thing = InterestingThings(
            title=item["title"],
            summary=item["summary"],
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
    # Log the title, category, URL, and summary of each item
    for thing in all_things:
        logger.info(f"{thing.title}, {thing.category}, {thing.url}, {thing.summary}")


async def add_posts():
    # Get the user record for 'admin'
    user = await db_ops.read_one_record(Select(Users).where(Users.user_name == "admin"))
    categories = await db_ops.read_query(Select(Categories))
    categories = [cat.to_dict() for cat in categories]
    cat_list = [cat["name"] for cat in categories]

    for _ in tqdm(range(30)):
        rand_cat = random.randint(0, len(cat_list) - 1)
        tags = [silly.noun() for _ in range(random.randint(2, 5))]
        date_created = datetime.now(UTC) - timedelta(days=random.randint(1, 700))
        post = Posts(
            title=silly.title(),
            content=silly.markdown(),
            user_id=user.pkid,
            category=str(cat_list[rand_cat]).lower(),
            tags=tags,
            date_created=date_created,
        )
        # Try to add the new item to the database
        try:
            data = await db_ops.create_one(post)
            logger.info(f"adding demo posts {data}")
        except Exception as e:
            # If there's an error while adding the item, log the error
            logger.error(e)
