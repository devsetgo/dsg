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
from typing import List, Tuple, Union, Dict, Any, Optional
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

# Initialize Jinja2 templates with the specified directory
templates = Jinja2Templates(directory="templates")

# Serve static files from the specified directory
statics = StaticFiles(directory="static")

# Log the start of database operations setup
logger.info("setting up database operations")

# Initialize database operations with the asynchronous database instance
db_ops = database_operations.DatabaseOperations(async_db)

# Log the completion of database setup
logger.info("database setup complete")


async def startup() -> None:
    """
    Start up the application.

    This asynchronous function performs the following tasks:
    - Logs that the services are starting up.
    - Checks the database for existing tables.
    - Creates the database tables if they do not exist.
    - Logs the names of the tables that have been created.
    - Adds system data to the database if no users are found.
    - Downloads a specified spaCy model.

    This function is typically called when the application starts up.
    """
    # Log the start of the services
    logger.info("starting up services")

    # Log the check for existing database tables
    logger.info("checking database for tables")

    # Retrieve the list of existing table names
    tables: List[str] = await db_ops.get_table_names()

    # Log the creation of database tables
    logger.info(f"creating database tables {tables}")

    # Create the database tables if they do not exist
    await async_db.create_tables()
    logger.info("database tables created")

    # Retrieve the updated list of table names
    tables = await db_ops.get_table_names()
    logger.info(f"tables {tables} have been created")

    # Check if there are any users in the database
    user = await db_ops.read_query(Select(Users))
    if len(user) == 0:
        # Add system data if no users are found
        await add_system_data()

    # Specify the spaCy model to download
    model_name: str = "xx_ent_wiki_sm"

    # Download the specified spaCy model
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
    flag_file_path: str = f"/tmp/{model_name}_downloaded.flag"

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

    This asynchronous function performs the following tasks:
    - Logs that the services are shutting down.
    - Disconnects from the database.

    This function is typically called when the application is shutting down.

    Args:
        None

    Returns:
        None
    """

    # Log that the services are shutting down
    logger.info("shutting down services")

    # Disconnect from the database
    logger.info("disconnecting from database")
    await async_db.disconnect()
    logger.info("disconnected from database")
    print("That's all folks!")


async def add_system_data() -> None:
    """
    Add system data to the database.

    This asynchronous function performs the following tasks based on the settings:
    - Creates an admin user if `create_admin_user` is True.
    - Creates demo notes for the admin user if `create_demo_notes` is True and the environment is not production.
    - Creates demo users and their notes if `create_demo_user` is True and the environment is not production.
    - Creates base categories if `create_base_categories` is True and the environment is not production.
    - Creates demo data including web links and posts if `create_demo_data` is True and the environment is not production.

    This function is typically called during the application startup to ensure that
    essential system data is present in the database.

    Args:
        None

    Returns:
        None
    """
    # Check if admin user creation is enabled in settings
    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        data: Dict[str, Any] = await add_admin()  # Create an admin user

        # Check if the environment is not production and demo notes creation is enabled
        if settings.release_env.lower() != "prd":
            if settings.create_demo_notes is True:
                await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    # Check if the environment is not production
    if settings.release_env.lower() != "prd":
        # Check if demo user creation is enabled in settings
        if settings.create_demo_user is True:
            logger.warning("Creating demo user")
            for _ in tqdm(
                range(settings.create_demo_users_qty),
                desc="creating demo users",
                leave=True,
            ):
                data = await add_user()  # Create a demo user
                await add_notes(user_id=data["pkid"])  # Create notes for the loop user

        # Check if base categories creation is enabled in settings
        if settings.create_base_categories is True:
            logger.warning("Creating base categories")
            await add_categories()  # Create base categories

        # Check if demo data creation is enabled in settings
        if settings.create_demo_data is True:
            logger.warning("Creating demo data")
            await add_web_links()  # Create demo data
            await add_posts()

            from .functions.pypi_core import add_demo_data

            await add_demo_data(qty=20)


async def add_system_data() -> None:
    """
    Add system data to the database.

    This asynchronous function performs the following tasks based on the settings:
    - Creates an admin user if `create_admin_user` is True.
    - Creates demo notes for the admin user if `create_demo_notes` is True and the environment is not production.
    - Creates demo users and their notes if `create_demo_user` is True and the environment is not production.
    - Creates base categories if `create_base_categories` is True and the environment is not production.
    - Creates demo data including web links and posts if `create_demo_data` is True and the environment is not production.

    This function is typically called during the application startup to ensure that
    essential system data is present in the database.

    Args:
        None

    Returns:
        None
    """
    # Check if admin user creation is enabled in settings
    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        data: Dict[str, Any] = await add_admin()  # Create an admin user

        # Check if the environment is not production and demo notes creation is enabled
        if settings.release_env.lower() != "prd":
            if settings.create_demo_notes is True:
                await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    # Check if the environment is not production
    if settings.release_env.lower() != "prd":
        # Check if demo user creation is enabled in settings
        if settings.create_demo_user is True:
            logger.warning("Creating demo user")
            for _ in tqdm(
                range(settings.create_demo_users_qty),
                desc="creating demo users",
                leave=True,
            ):
                data = await add_user()  # Create a demo user
                await add_notes(user_id=data["pkid"])  # Create notes for the loop user

        # Check if base categories creation is enabled in settings
        if settings.create_base_categories is True:
            logger.warning("Creating base categories")
            await add_categories()  # Create base categories

        # Check if demo data creation is enabled in settings
        if settings.create_demo_data is True:
            logger.warning("Creating demo data")
            await add_web_links()  # Create demo data
            await add_posts()

            from .functions.pypi_core import add_demo_data

            await add_demo_data(qty=20)


async def add_system_data() -> None:
    """
    Add system data to the database.

    This asynchronous function performs the following tasks based on the settings:
    - Creates an admin user if `create_admin_user` is True.
    - Creates demo notes for the admin user if `create_demo_notes` is True and the environment is not production.
    - Creates demo users and their notes if `create_demo_user` is True and the environment is not production.
    - Creates base categories if `create_base_categories` is True and the environment is not production.
    - Creates demo data including web links and posts if `create_demo_data` is True and the environment is not production.

    This function is typically called during the application startup to ensure that
    essential system data is present in the database.

    Args:
        None

    Returns:
        None
    """
    # Check if admin user creation is enabled in settings
    if settings.create_admin_user is True:
        logger.warning("Creating admin user")
        data: Dict[str, Any] = await add_admin()  # Create an admin user

        # Check if the environment is not production and demo notes creation is enabled
        if settings.release_env.lower() != "prd":
            if settings.create_demo_notes is True:
                await add_notes(user_id=data["pkid"])  # Create notes for the admin user

    # Check if the environment is not production
    if settings.release_env.lower() != "prd":
        # Check if demo user creation is enabled in settings
        if settings.create_demo_user is True:
            logger.warning("Creating demo user")
            for _ in tqdm(
                range(settings.create_demo_users_qty),
                desc="creating demo users",
                leave=True,
            ):
                data = await add_user()  # Create a demo user
                await add_notes(user_id=data["pkid"])  # Create notes for the loop user

        # Check if base categories creation is enabled in settings
        if settings.create_base_categories is True:
            logger.warning("Creating base categories")
            await add_categories()  # Create base categories

        # Check if demo data creation is enabled in settings
        if settings.create_demo_data is True:
            logger.warning("Creating demo data")
            await add_web_links()  # Create demo data
            await add_posts()

            from .functions.pypi_core import add_demo_data

            await add_demo_data(qty=20)


async def add_user() -> Dict[str, Any]:
    """
    Add a system user to the database.

    This asynchronous function performs the following tasks:
    - Generates a random user name using the `silly` library and `secrets` module.
    - Randomly assigns roles to the user.
    - Creates a `Users` object with random attributes.
    - Attempts to add the user to the database.
    - Retrieves the user from the database and returns the user's data as a dictionary.

    This function is typically used to add demo or system users to the database.

    Args:
        None

    Returns:
        Dict[str, Any]: A dictionary containing the user's data.
    """
    logger.info("adding system user")

    # Generate a random user name
    import secrets

    user_name: str = f"{silly.plural()}-{silly.noun()}{secrets.token_hex(2)}".lower()

    # Define possible roles and randomly assign them to the user
    roles: List[str] = ["notes", "web_links", "job_applications", "developer", "posts"]
    role_data: Dict[str, bool] = {}
    for role in roles:
        if random.choice([True, False]):
            role_data[role] = random.choice([True, False])

    # Create a Users object with random attributes
    user = Users(
        first_name=f"{silly.verb()}",
        last_name=f"{silly.noun()}",
        user_name=user_name,
        # password=hashed_password,  # Uncomment and set the hashed password if needed
        is_active=random.choice([True, False]),
        is_admin=random.choice([True, False]),
        roles=role_data,
        is_locked=random.choice([True, False]),
        date_last_login=datetime.utcnow(),
    )

    try:
        # Attempt to add the user to the database
        await db_ops.create_one(user)

        # Retrieve the user from the database
        user = await db_ops.read_one_record(
            Select(Users).where(Users.user_name == user_name)
        )

        # Log the user's full name
        logger.info(user.full_name)

        # Return the user's data as a dictionary
        return user.to_dict()

    except Exception as e:
        # Log any errors that occur during the process
        logger.error(e)
        return {}


async def add_categories() -> None:
    """
    Add system categories to the database if they do not already exist.

    This asynchronous function performs the following tasks:
    - Checks if there are any categories in the database.
    - If no categories are found, it adds a predefined list of categories.
    - Logs the addition of each category and any errors that occur during the process.
    - Retrieves and logs all categories from the database.

    This function is typically called during the application startup to ensure that
    essential system categories are present in the database.

    Args:
        None

    Returns:
        None
    """

    # Count the number of existing categories in the database
    cat_number: int = await db_ops.count_query(
        query=Select(func.count(Categories.pkid))
    )

    # If categories already exist, log the information and return
    if cat_number != 0:
        logger.info("System categories already added")
        return

    # List of categories to be added, sorted alphabetically
    cat: List[str] = [
        "humor",
        "news",
        "other",
        "programming",
        "science",
        "technology",
        "woodworking",
    ]
    user_name: str = settings.admin_user.get_secret_value()

    # Retrieve the admin user record
    await db_ops.read_one_record(Select(Users).where(Users.user_name == user_name))

    # Add each category to the database
    for c in cat:
        logger.info(f"Adding system category {c}")
        category = Categories(
            name=c.title(),
            description=f"{str(c).title()} related items",
            is_system=True,
            is_post=True,
            is_weblink=True,
        )
        try:
            # Attempt to create the category in the database
            await db_ops.create_one(category)
        except Exception as e:
            # Log any error that occurs during the creation process
            logger.error(e)

    # Retrieve and log all categories from the database
    data: List[Categories] = await db_ops.read_query(Select(Categories))
    for d in data:
        logger.info(f"Category name: {d.name}")


async def add_web_links() -> None:
    """
    Add a list of web links to the database.

    This asynchronous function performs the following tasks:
    - Reads a list of web links from a JSON file.
    - Checks if each web link already exists in the database.
    - If a web link does not exist, it adds the web link to the database.
    - Logs the addition of each web link and any errors that occur during the process.
    - Retrieves and logs all web links from the database.

    This function is typically used to populate the database with a predefined list of web links.

    Args:
        None

    Returns:
        None
    """
    # Import the function to open a JSON file
    from dsg_lib.common_functions.file_functions import open_json

    # Read the list of web links from the JSON file
    my_stuff: List[Dict[str, Any]] = open_json("web_links.json")

    # Check to see if the items are already in the database
    for item in my_stuff:
        # Query the database for each item by title
        data: List[WebLinks] = await db_ops.read_query(
            Select(WebLinks).where(WebLinks.title == item["title"])
        )
        # If the item already exists in the database, log a message and return
        if len(data) > 0:
            logger.info(f"system item {item['title']} already added")
            return

    # Get the admin user name from the settings
    user_name: str = settings.admin_user.get_secret_value()
    # Get the user record for 'admin'
    user: Users = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

    # Loop through the list of items
    for item in my_stuff:
        # Get the category record for the current item
        category: Categories = await db_ops.read_one_record(
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
    all_things: List[WebLinks] = await db_ops.read_query(Select(WebLinks))
    # Log the title, category, URL, and summary of each item
    for thing in all_things:
        logger.info(f"{thing.title}, {thing.category}, {thing.url}, {thing.summary}")


async def add_posts() -> None:
    """
    Add demo posts to the database.

    This asynchronous function performs the following tasks:
    - Retrieves the admin user from the database.
    - Retrieves all categories from the database.
    - Checks if there are any existing posts in the database.
    - If no posts are found, it creates a predefined number of demo posts.
    - Logs the addition of each post and any errors that occur during the process.

    This function is typically used to populate the database with demo posts.

    Args:
        None

    Returns:
        None
    """
    # Get the admin user name from the settings
    user_name: str = settings.admin_user.get_secret_value()

    # Get the user record for 'admin'
    user: Users = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

    # Retrieve all categories from the database
    categories: List[Categories] = await db_ops.read_query(Select(Categories))
    categories_dict: List[Dict[str, Any]] = [cat.to_dict() for cat in categories]
    cat_list: List[str] = [cat["name"] for cat in categories_dict]

    # Check if there are any existing posts in the database
    posts: List[Posts] = await db_ops.read_query(Select(Posts))
    if len(posts) == 0:
        # Create a predefined number of demo posts
        for _ in tqdm(range(5), desc="creating demo posts", leave=False):
            rand_cat: int = random.randint(0, len(cat_list) - 1)
            tags: List[str] = [silly.noun() for _ in range(random.randint(2, 5))]
            date_created: datetime = datetime.now(UTC) - timedelta(
                days=random.randint(1, 700)
            )
            post = Posts(
                title=silly.sentence(),
                content=silly.markdown(length=random.randint(30, 60)),
                user_id=user.pkid,
                category=str(cat_list[rand_cat]).lower(),
                tags=tags,
                date_created=date_created,
            )
            # Try to add the new post to the database
            try:
                data: Posts = await db_ops.create_one(post)
                logger.info(f"adding demo posts {data}")
            except Exception as e:
                # If there's an error while adding the post, log the error
                logger.error(e)
