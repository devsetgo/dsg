# -*- coding: utf-8 -*-
"""
This module, `resources.py`, centralizes the management and provisioning of shared resources within the application. It is designed to streamline the access and manipulation of various resources such as templates for HTML rendering, static files for web content, and database operations for data persistence.

The module abstracts the complexity of initializing and configuring these resources, offering a simplified interface for the rest of the application. By centralizing resource management, it facilitates consistency and reusability across different parts of the application.

Module Attributes:
    templates (Jinja2Templates): Manages the rendering of HTML templates, providing a bridge between Python code and HTML output.
    statics (StaticFiles): Handles the serving of static files, such as CSS, JavaScript, and images, essential for web content.
    db_ops (DatabaseOperations): Encapsulates database operations, offering a unified interface for CRUD operations and database transactions.

Functions:
    startup: Initializes the resources required by the application, ensuring they are ready for use when the application starts. This function is asynchronous to accommodate the initialization of resources that may require IO operations, such as database connections.

Author:
    Mike Ryan

License:
    MIT License
"""
import os
import random
from datetime import UTC, datetime, timedelta

import silly
import spacy
from dsg_lib.async_database_functions import database_operations
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from sqlalchemy import Select, func
from tqdm import tqdm

from .db_init import async_db
from .db_tables import Categories, InterestingThings, Notes, Posts, Users
from .functions.models import RoleEnum
from .settings import settings

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
    logger.info(f"creating database tables {tables}")

    # if tables.__len__() == 0:
    await async_db.create_tables()
    logger.info("database tables created")
    tables = await db_ops.get_table_names()
    logger.info(f"tables {tables} have been created")

    user = await db_ops.read_query(Select(Users))
    if len(user) == 0:
        await add_system_data()

    model_name = "xx_ent_wiki_sm"
    download_spacy_model(model_name)


def download_spacy_model(model_name: str):
    """
    Downloads the specified spaCy model if it is not already installed.

    This function checks for the presence of a flag file in the /tmp directory
    to determine if the model has been downloaded previously. If the model is not
    found, it attempts to download and install the model. Upon successful download,
    a flag file is created to indicate the model's availability for future checks.

    Args:
        model_name (str): The name of the spaCy model to download, e.g., "xx_ent_wiki_sm".

    Returns:
        None
    """
    # Path to a flag file which indicates whether the model has been downloaded
    flag_file_path = f"/tmp/{model_name}_downloaded.flag"

    # Check if the flag file exists, indicating the model has already been downloaded
    if os.path.exists(flag_file_path):
        logger.info(f"Model '{model_name}' is already installed. No download needed.")
        return

    try:
        # Attempt to load the model to check if it's already installed
        spacy.load(model_name)
        logger.info(f"Model '{model_name}' found. No download needed.")
    except OSError:
        # Model not installed, proceed with download
        logger.info(f"Model '{model_name}' not found. Starting download...")
        try:
            spacy.cli.download(model_name)
            logger.info(f"Model '{model_name}' downloaded successfully.")

            # Create a flag file to indicate the model has been downloaded
            with open(flag_file_path, "w") as f:
                f.write("Downloaded")
        except Exception as e:
            # Log any error during the download process
            logger.error(f"Failed to download model '{model_name}'. Error: {e}")


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

        if settings.release_env.lower() != "prd":
            if settings.create_demo_notes is True:
                await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    if settings.release_env.lower() != "prd":
        if settings.create_demo_user is True:
            logger.warning("Creating demo user")
            for _ in tqdm(
                range(settings.create_demo_users_qty),
                desc="creating demo users",
                leave=True,
            ):
                data = await add_user()  # Create a demo user
                await add_notes(user_id=data["pkid"])  # Create notes for the loop user

        if settings.create_base_categories is True:
            logger.warning("Creating base categories")
            await add_categories()  # Create base categories

        if settings.create_demo_data is True:
            logger.warning("Creating demo data")
            await add_interesting_things()  # Create demo data
            await add_posts()

            from .functions.pypi_core import add_demo_data

            await add_demo_data(qty=20)
            # await fake_login_attempts()


async def fake_login_attempts():
    from .endpoints.users import fail_logging

    for _ in tqdm(range(10), desc="fake login attempts", leave=True):
        await fail_logging(
            user_name=silly.noun(),
            # password=silly.thing(),
            meta_data={
                "host": "localhost:5000",
                "connection": "keep-alive",
                "content-length": "29",
                "sec-ch-ua": '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
                "dnt": "1",
                "hx-current-url": "http://localhost:5000/users/login",
                "sec-ch-ua-mobile": "?0",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0",
                "content-type": "application/x-www-form-urlencoded",
                "hx-request": "true",
                "sec-ch-ua-platform": '"Windows"',
                "accept": "*/*",
                "origin": "http://localhost:5000",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "http://localhost:5000/users/login",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-US,en;q=0.9",
            },
        )


async def add_admin():
    if settings.create_admin_user is True:
        logger.warning("creating admin user")
        user_name = settings.admin_user.get_secret_value()
        settings.admin_password.get_secret_value()

        add_roles = {}
        for role in RoleEnum:
            add_roles[role] = True

        # hashed_password = hash_password(password)
        user = Users(
            first_name="Admin",
            last_name="User",
            user_name=user_name,
            # password=hashed_password,
            email=settings.admin_email,
            my_timezone=settings.default_timezone,
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
            print(e)


async def add_notes(user_id: str, qty_notes: int = settings.create_demo_notes_qty):
    moods = ["positive", "neutral", "negative"]
    mood_analysis = [mood[0] for mood in settings.mood_analysis_weights]

    for i in tqdm(range(5), desc=f"same day notes for {user_id}", leave=False):
        mood = random.choice(moods)
        mood_analysis_choice = random.choice(mood_analysis)

        length = random.randint(5, 20)
        note = silly.paragraph(length=length)
        summary = note[:50]
        tags = list({silly.adjective() for x in range(1, 4)})

        # Make date_updated the same as date_created or 3-15 days later
        date_created = datetime.now(UTC) - timedelta(days=365 * i)

        date_updated = date_created
        note = Notes(
            mood="positive",
            note=f"{user_id} This is a note that was created in the past",
            summary="Past Note",
            tags=list({silly.adjective() for x in range(1, 4)}),
            mood_analysis="positive",
            user_id=user_id,
            date_created=date_created,
            date_updated=date_updated,
        )
        await db_ops.create_one(note)

    for _ in tqdm(
        range(qty_notes), desc=f"creating demo notes for {user_id}", leave=False
    ):
        mood = random.choice(moods)
        mood_analysis_choice = random.choice(mood_analysis)

        length = random.randint(5, 20)
        note = silly.paragraph(length=length)
        summary = note[:50]
        tags = list({silly.adjective() for x in range(1, 4)})

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
        await db_ops.create_one(note)


async def add_user():
    logger.info("adding system user")
    # hashed_password = hash_password("password")
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
        # password=hashed_password,
        is_active=random.choice([True, False]),
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
    user_name = settings.admin_user.get_secret_value()
    await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

    for c in cat:
        logger.info(f"adding system category {c}")
        category = Categories(
            name=c.title(),
            description=f"{str(c).title()} related items",
            is_system=True,
            is_post=True,
            is_thing=True,
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
    from dsg_lib.common_functions.file_functions import open_json

    my_stuff = open_json("interesting_things.json")
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
    user_name = settings.admin_user.get_secret_value()
    # Get the user record for 'admin'
    user = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

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
            logger.debug(thing)
        except Exception as e:
            # If there's an error while adding the item, log the error
            logger.error(f"thing error: {e}")

    # Get all items from the InterestingThings table
    all_things = await db_ops.read_query(Select(InterestingThings))
    # Log the title, category, URL, and summary of each item
    for thing in all_things:
        logger.info(f"{thing.title}, {thing.category}, {thing.url}, {thing.summary}")


async def add_posts():
    user_name = settings.admin_user.get_secret_value()
    # Get the user record for 'admin'
    user = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )
    categories = await db_ops.read_query(Select(Categories))
    categories = [cat.to_dict() for cat in categories]
    cat_list = [cat["name"] for cat in categories]
    posts = await db_ops.read_query(Select(Posts))
    if len(posts) == 0:
        for _ in tqdm(range(5), desc="creating demo posts", leave=False):
            rand_cat = random.randint(0, len(cat_list) - 1)
            tags = [silly.noun() for _ in range(random.randint(2, 5))]
            date_created = datetime.now(UTC) - timedelta(days=random.randint(1, 700))
            post = Posts(
                title=silly.sentence(),
                content=silly.markdown(length=random.randint(30, 60)),
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
