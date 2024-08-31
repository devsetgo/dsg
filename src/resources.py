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
    add_notes: Adds demo notes for a given user, generating notes with random moods, mood analyses, tags, and timestamps.
    add_admin: Creates an admin user if the settings indicate to do so, with specified roles and logs the creation process.

Imports:
    os: Provides a way of using operating system dependent functionality.
    random: Implements pseudo-random number generators for various distributions.
    datetime: Supplies classes for manipulating dates and times.
    silly: Generates random text for testing purposes.
    spacy: Industrial-strength Natural Language Processing (NLP) with Python and Cython.
    database_operations: Contains asynchronous database operation functions.
    StaticFiles: Handles the serving of static files.
    Jinja2Templates: Manages the rendering of HTML templates.
    logger: Logging library for Python.
    Select, func: SQLAlchemy functions for database operations.
    tqdm: Provides a fast, extensible progress bar for loops and other operations.

Author:
    Mike Ryan

License:
    MIT License
"""
import os
import random
from datetime import UTC, datetime, timedelta
from typing import List, Optional, Tuple, Union, Dict, Any
import silly
import spacy
from dsg_lib.async_database_functions import database_operations
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from sqlalchemy import Select, func
from tqdm import tqdm

from .db_init import async_db
from .db_tables import Categories, Notes, Posts, Users, WebLinks
from .functions.models import RoleEnum
from .settings import settings
# templates and static files
templates = Jinja2Templates(directory="templates")
statics = StaticFiles(directory="static")

# Log the initialization of database operations
logger.info("setting up database operations")

# Initialize the database operations with the async database instance
db_ops = database_operations.DatabaseOperations(async_db)

# Log the completion of the database setup
logger.info("database setup complete")

async def startup() -> None:
    """
    Start up the application.

    This asynchronous function initializes the application by performing the following tasks:
    - Logs that the services are starting up.
    - Checks the database for existing tables.
    - Creates the database tables if they don't exist.
    - Logs the names of the tables that have been created.
    - Adds system data to the database if no users are found.
    - Downloads the specified spaCy model for NLP tasks.

    This function is typically called when the application starts up.

    Returns:
        None
    """
    # Log the startup process
    logger.info("starting up services")
    
    # Check the database for existing tables
    logger.info("checking database for tables")
    tables: List[str] = await db_ops.get_table_names()
    logger.info(f"creating database tables {tables}")

    # Create database tables if they don't exist
    await async_db.create_tables()
    logger.info("database tables created")
    
    # Log the names of the tables that have been created
    tables = await db_ops.get_table_names()
    logger.info(f"tables {tables} have been created")

    # Check if there are any users in the database
    user = await db_ops.read_query(Select(Users))
    if len(user) == 0:
        # Add system data if no users are found
        await add_system_data()

    # Download the specified spaCy model for NLP tasks
    model_name = "xx_ent_wiki_sm"
    download_spacy_model(model_name)


def download_spacy_model(model_name: str) -> None:
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
            # Download the spaCy model
            spacy.cli.download(model_name)
            logger.info(f"Model '{model_name}' downloaded successfully.")

            # Create a flag file to indicate the model has been downloaded
            with open(flag_file_path, "w") as f:
                f.write("Downloaded")
        except Exception as e:
            # Log any error during the download process
            logger.error(f"Failed to download model '{model_name}'. Error: {e}")


async def shutdown() -> None:
    """
    Shut down the application.

    This asynchronous function is responsible for gracefully shutting down the application.
    It performs the following tasks:
    - Logs that the services are shutting down.
    - Disconnects from the database.

    This function is typically called when the application is shutting down.

    Returns:
        None
    """
    # Log that the services are shutting down
    logger.info("shutting down services")

    # Disconnect from the database
    logger.info("disconnecting from database")
    await async_db.disconnect()


async def add_system_data() -> None:
    """
    Add system data to the application.

    This asynchronous function initializes the system data based on the settings.
    It performs the following tasks:
    - Creates an admin user if specified in the settings.
    - Creates demo notes for the admin user if specified and not in production environment.
    - Creates demo users and their notes if specified and not in production environment.
    - Creates base categories if specified and not in production environment.
    - Creates demo data including web links and posts if specified and not in production environment.

    This function is typically called during the startup process to ensure the system
    has the necessary initial data.

    Returns:
        None
    """
    # Check if an admin user should be created
    if settings.create_admin_user:
        logger.warning("Creating admin user")
        data: Optional[Dict[str, Any]] = await add_admin()  # Create an admin user

        # Check if demo notes should be created for the admin user
        if settings.release_env.lower() != "prd" and settings.create_demo_notes:
            await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    # Check if the environment is not production
    if settings.release_env.lower() != "prd":
        # Check if demo users should be created
        if settings.create_demo_user:
            logger.warning("Creating demo user")
            for _ in tqdm(
                range(settings.create_demo_users_qty),
                desc="creating demo users",
                leave=True,
            ):
                data = await add_user()  # Create a demo user
                await add_notes(user_id=data["pkid"])  # Create notes for the loop user

        # Check if base categories should be created
        if settings.create_base_categories:
            logger.warning("Creating base categories")
            await add_categories()  # Create base categories

        # Check if demo data should be created
        if settings.create_demo_data:
            logger.warning("Creating demo data")
            await add_web_links()  # Create demo data
            await add_posts()

            from .functions.pypi_core import add_demo_data

            await add_demo_data(qty=20)



async def add_admin() -> Optional[Dict[str, Any]]:
    """
    Create an admin user if the settings indicate to do so.

    This asynchronous function checks the settings to determine if an admin user should be created.
    If so, it creates the admin user with the specified roles and logs the creation process.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representation of the created admin user, or None if an error occurs.
    """
    # Check if the settings indicate to create an admin user
    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        
        # Retrieve admin user credentials from settings
        user_name = settings.admin_user.get_secret_value()
        settings.admin_password.get_secret_value()

        # Define roles for the admin user
        add_roles = {}
        for role in RoleEnum:
            add_roles[role] = True

        # Create a new Users instance for the admin user
        user = Users(
            first_name="Admin",
            last_name="User",
            user_name=user_name,
            # password=hashed_password,  # Uncomment and set hashed password if needed
            email=settings.admin_email,
            my_timezone=settings.default_timezone,
            is_active=True,
            is_admin=True,
            roles=add_roles,
        )

        try:
            # Attempt to create the admin user in the database
            res = await db_ops.create_one(user)
            logger.debug(f"Admin user created: {res.to_dict()}")

            # Retrieve the created admin user from the database
            user = await db_ops.read_one_record(
                Select(Users).where(Users.user_name == user_name)
            )

            logger.warning(f"Admin created: {user.full_name}")
            return user.to_dict()
        except Exception as e:
            # Log any errors that occur during the creation process
            logger.error(e)
            print(e)
            return None


async def add_notes(user_id: str, qty_notes: int = settings.create_demo_notes_qty) -> None:
    """
    Add demo notes for a given user.

    This asynchronous function creates a specified quantity of demo notes for a user.
    It generates notes with random moods, mood analyses, tags, and timestamps. Some notes
    are created with the same date for both creation and update, while others have a random
    update date.

    Args:
        user_id (str): The ID of the user for whom the notes are being created.
        qty_notes (int, optional): The quantity of demo notes to create. Defaults to settings.create_demo_notes_qty.

    Returns:
        None
    """
    # Define possible moods and mood analyses
    moods: List[str] = ["positive", "neutral", "negative"]
    mood_analysis: List[str] = [mood[0] for mood in settings.mood_analysis_weights]

    # Create notes with the same date for both creation and update
    for i in tqdm(range(5), desc=f"same day notes for {user_id}", leave=False):
        mood: str = random.choice(moods)
        mood_analysis_choice: str = random.choice(mood_analysis)

        length: int = random.randint(5, 20)
        note_text: str = silly.paragraph(length=length)
        summary: str = note_text[:50]
        tags: List[str] = list({silly.adjective() for _ in range(1, 4)})

        # Make date_updated the same as date_created or 3-15 days later
        date_created: datetime = datetime.now(UTC) - timedelta(days=365 * i)
        date_updated: datetime = date_created

        # Create the note
        note = Notes(
            mood=mood,
            note=note_text,
            summary=summary,
            tags=tags,
            mood_analysis=mood_analysis_choice,
            user_id=user_id,
            demo_created=1,
            date_created=date_created,
            date_updated=date_updated,
        )
        await db_ops.create_one(note)

    # Create notes with random dates within the last X years
    for _ in tqdm(range(qty_notes), desc=f"creating demo notes for {user_id}", leave=False):
        mood: str = random.choice(moods)
        mood_analysis_choice: str = random.choice(mood_analysis)

        length: int = random.randint(5, 20)
        note_text: str = silly.paragraph(length=length)
        summary: str = note_text[:50]
        tags: List[str] = list({silly.adjective() for _ in range(1, 4)})

        # Generate a random date within the last X years
        days_in_three_years: int = 365 * 12
        random_number_of_days: int = random.randrange(days_in_three_years)
        date_created: datetime = datetime.now(UTC) - timedelta(days=random_number_of_days)

        # Make date_updated the same as date_created or 3-15 days later
        days_to_add: int = random.choice([0] + list(range(3, 16)))
        date_updated: datetime = date_created + timedelta(days=days_to_add)

        # Convert the timezone-aware datetimes to timezone-naive datetimes
        date_created = date_created.replace(tzinfo=None)
        date_updated = date_updated.replace(tzinfo=None)

        # Create the note
        note = Notes(
            mood=mood,
            note=note_text,
            summary=summary,
            tags=tags,
            demo_created=1,
            mood_analysis=mood_analysis_choice,
            user_id=user_id,
            date_created=date_created,
            date_updated=date_updated,
        )
        await db_ops.create_one(note)


async def add_user() -> Optional[Dict[str, Any]]:
    """
    Add a system user.

    This asynchronous function creates a new user with random attributes such as
    first name, last name, username, roles, and status flags. It logs the process
    of adding the user and returns a dictionary representation of the created user.

    Returns:
        Optional[Dict[str, Any]]: A dictionary representation of the created user, or None if an error occurs.
    """
    logger.info("adding system user")
    
    # Generate a random username using silly and secrets libraries
    import secrets
    user_name: str = f"{silly.plural()}-{silly.noun()}{secrets.token_hex(2)}".lower()
    
    # Define possible roles for the user
    roles: List[str] = ["notes", "web_links", "job_applications", "developer", "posts"]
    role_data: Dict[str, bool] = {}

    # Randomly assign roles to the user
    for role in roles:
        if random.choice([True, False]):
            role_data[role] = random.choice([True, False])

    # Create a new Users instance with random attributes
    user = Users(
        first_name=f"{silly.verb()}",
        last_name=f"{silly.noun()}",
        user_name=user_name,
        # password=hashed_password,  # Uncomment and set hashed password if needed
        is_active=random.choice([True, False]),
        is_admin=random.choice([True, False]),
        roles=role_data,
        is_locked=random.choice([True, False]),
        date_last_login=datetime.utcnow(),
    )
    
    try:
        # Attempt to create the user in the database
        await db_ops.create_one(user)
        
        # Retrieve the created user from the database
        user = await db_ops.read_one_record(
            Select(Users).where(Users.user_name == user_name)
        )
        logger.info(user.full_name)
        return user.to_dict()
    except Exception as e:
        # Log any errors that occur during the creation process
        logger.error(e)
        return None


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

    cat: list = ["news", "other", "programming", "science", "sites","science", "technology", "woodworking"]
    user_name = settings.admin_user.get_secret_value()
    await db_ops.read_one_record(Select(Users).where(Users.user_name == user_name))

    for c in cat:
        logger.info(f"adding system category {c}")
        category = Categories(
            name=c.title(),
            description=f"{str(c).title()} related items",
            is_system=True,
            is_post=True,
            is_weblink=True,
        )
        try:
            await db_ops.create_one(category)
        except Exception as e:
            logger.error(e)
    data = await db_ops.read_query(Select(Categories))

    for d in data:
        logger.info(f"category name: {d.name}")



async def add_web_links():
    # This function is responsible for adding a list of interesting things to the database.
    # Each item in the list is a dictionary with keys for name, description, url, and category.

    # Define the list of items to be added
    from dsg_lib.common_functions.file_functions import open_json

    my_stuff = open_json("web_links.json")
    # Check to see if the items are already in the database
    for item in my_stuff:
        # Query the database for each item by name
        data = await db_ops.read_query(
            Select(WebLinks).where(WebLinks.title == item["title"])
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
        # Create a new WebLinks instance with the item details
        thing = WebLinks(
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

    # Get all items from the WebLinks table
    all_things = await db_ops.read_query(Select(WebLinks))
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