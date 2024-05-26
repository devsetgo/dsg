# -*- coding: utf-8 -*-
"""
This module, `resources.py`, is responsible for managing and handling resources in the application.

It includes functions and classes for loading, manipulating, and saving resources. The specific resources it handles can vary,
but they might include things like images, audio files, configuration files, or other data files used by the application.

The module also includes setup for database operations and static files.

Module Attributes:
    templates (Jinja2Templates): An instance of `Jinja2Templates` for rendering templates.
    statics (StaticFiles): An instance of `StaticFiles` for serving static files.
    db_ops (DatabaseOperations): An instance of `DatabaseOperations` for performing database operations.

Functions:
    startup: An asynchronous function that is used to start up the application.

Please refer to the individual function or class docstrings for more specific information about what each part of the module does.
"""
import random
from datetime import UTC, datetime, timedelta

import silly
from dsg_lib.async_database_functions import database_operations
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from loguru import logger
from sqlalchemy import Select, func
from tqdm import tqdm

from .db_init import async_db
from .db_tables import Categories, InterestingThings, Notes, Posts, Users
from .functions.hash_function import hash_password
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

    if settings.create_demo_user is True:
        logger.warning("Creating demo user")
        for _ in tqdm(
            range(settings.create_demo_users_qty),
            desc="creating demo users",
            leave=True,
        ):
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
        await fake_login_attempts()


async def fake_login_attempts():
    from .endpoints.users import fail_logging

    for _ in tqdm(range(100),desc="fake login attempts",leave=True):
        await fail_logging(
            user_name=silly.noun(),
            password=silly.thing(),
            meta_data={},
            real_id=False,
        )


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
            last_name="User",
            user_name=user_name,
            password=hashed_password,
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
    user_name = settings.admin_user.get_secret_value()
    user = await db_ops.read_one_record(
        Select(Users).where(Users.user_name == user_name)
    )

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
            "title": "DevSetGo Library",
            "summary": "A helper library I use for my Python projects.",
            "url": "https://devsetgo.github.io/devsetgo_lib/",
            "category": "programming",
        },
        {
            "title": "Pypi Checker",
            "summary": "Get the latest version of Python libraries.",
            "url": "/pypi",
            "category": "programming",
        },
        {
            "title": "FastAPI",
            "summary": "An async Python framework for building great APIs.",
            "url": "https://fastapi.tiangolo.com/",
            "category": "programming",
        },
        {
            "title": "Starlette",
            "summary": "An async Python framework for building sites and is what FastAPI is built on top of.",
            "url": "https://fastapi.tiangolo.com/",
            "category": "programming",
        },
        {
            "title": "Portainer",
            "summary": "How to manage containers for Docker or Kubernetes.",
            "url": "https://www.portainer.io/",
            "category": "technology",
        },
        {
            "title": "Digital Ocean",
            "summary": "Digital Ocean is a great hosting option for servers, apps, and Kubernetes (K8s), offering excellent documentation and tutorials. (referral link)",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "technology",
        },
        {
            "title": "Kubernetes",
            "summary": "Kubernetes is an open-source platform for automating the deployment, scaling, and management of containerized applications.",
            "url": "https://m.do.co/c/9a3b3c4fbc90",
            "category": "programming",
        },
        {
            "title": "Run your GitHub Actions locally",
            "summary": "Act is an open-source tool that allows you to run your GitHub Actions locally, enabling easier debugging and development of workflows before deploying them on GitHub.",
            "url": "https://github.com/nektos/act",
            "category": "programming",
        },
        {
            "title": "Testcontainers",
            "summary": "",
            "url": "https://youtu.be/sNg0bnMF_qY?si=nfZVvABhCbWPqJtu",
            "category": "programming",
        },
        {
            "title": "authentik Docker Compose Installation",
            "summary": "This guide provides step-by-step instructions for installing authentik, an open-source identity provider, using Docker Compose, simplifying the deployment and management of authentication services.",
            "url": "https://docs.goauthentik.io/docs/installation/docker-compose",
            "category": "programming",
        },
        {
            "title": "10 Free Software You Probably Didn't Know Existed!",
            "summary": "This video showcases 10 free software tools that are lesser-known but highly useful, covering a range of applications from productivity to creative work.",
            "url": "https://youtu.be/guIZLZVqEgQ?si=n-oUEEY-Q2hkImni",
            "category": "technology",
        },
        {
            "title": "Actionforge is a VS Code Extension to Build GitHub Workflows Visually",
            "summary": "",
            "url": "https://www.infoq.com/news/2024/03/actionforge-github-action-gui/",
            "category": "programming",
        },
        {
            "title": "Meet Netron: A Visualizer for Neural Network, Deep Learning and Machine Learning Models",
            "summary": "Netron is a tool for visualizing neural networks, deep learning, and machine learning models, providing an interactive interface to understand and analyze model architectures and parameters.",
            "url": "https://www.marktechpost.com/2024/01/02/meet-netron-a-visualizer-for-neural-network-deep-learning-and-machine-learning-models/",
            "category": "programming",
        },
        {
            "title": "Pandas AI",
            "summary": "Pandas AI is an open-source library that enhances the capabilities of the Pandas library by integrating AI features, making data analysis more intuitive and powerful.",
            "url": "https://github.com/gventuri/pandas-ai",
            "category": "programming",
        },
        {
            "title": "Meet PostgresML",
            "summary": "PostgresML is an open-source Python library that integrates with PostgreSQL, enabling the training and deployment of machine learning models directly within the database using SQL queries.",
            "url": "https://www.marktechpost.com/2023/12/27/meet-postgresml-an-open-source-python-library-that-integrates-with-postgresql-and-has-the-ability-to-train-and-deploy-machine-learning-ml-models-directly-within-the-database-using-sql-queries/",
            "category": "programming",
        },
        {
            "title": "AWS Well Architected",
            "summary": "This article reviews the AWS Well-Architected Framework, providing insights and best practices for designing and operating reliable, secure, efficient, and cost-effective cloud applications.",
            "url": "https://dev.to/aws-heroes/aws-well-architected-review-in-action-15a9",
            "category": "technology",
        },
        {
            "title": "COMPASS RG-1/RG-2 Universal Roller Guides",
            "summary": "The COMPASS RG-1/RG-2 Universal Roller Guides are woodworking accessories designed to provide smooth and precise material feed, enhancing safety and accuracy in various woodworking tasks.",
            "url": "https://www.harveywoodworking.com/products/universal-roller-guide",
            "category": "woodworking",
        },
        {
            "title": "isotunes.com/collections/earmuffs",
            "summary": "This webpage offers a collection of high-quality earmuffs from ISOtunes, designed to provide hearing protection with features like Bluetooth connectivity and noise cancellation.",
            "url": "https://isotunes.com/collections/earmuffs",
            "category": "woodworking",
        },
        {
            "title": "Custom GPT That Extracts Data from Websites",
            "summary": "This video tutorial demonstrates how to create a custom GPT model that extracts data from websites, showcasing techniques for web scraping and data processing using GPT technology.",
            "url": "https://youtu.be/pGHtjqvnSAQ?si=WJiyV2C6YGU-VrnS",
            "category": "programming",
        },
        {
            "title": "Ridgid R4222 Miter Saw Dust Collection Chute",
            "summary": "The Ridgid R4222 Miter Saw Dust Collection Chute is an accessory designed to enhance dust management for the Ridgid R4222 miter saw, improving cleanliness and visibility during cutting tasks.",
            "url": "https://shopnationstore.com/products/ridgid-r4222-miter-saw-dust-collection-chute",
            "category": "woodworking",
        },
        {
            "title": '19.5x14" Round Charcuterie Board With Handle Acrylic Router Template',
            "summary": 'This acrylic router template is designed for creating a 19.5x14" round charcuterie board with a handle, providing precise and repeatable cuts for woodworking projects.',
            "url": "https://craftedelements.com/products/19-5x14-round-charcuterie-board-with-handle-acrylic-router-template",
            "category": "woodworking",
        },
        {
            "title": "Kreg(R) Pocket-Hole Jig 720PRO",
            "summary": "The Kreg Pocket-Hole Jig 720PRO is a versatile and efficient tool designed for creating strong, precise pocket-hole joints in woodworking projects. It features advanced clamping and material support for ease of use.",
            "url": "https://www.kregtool.com/shop/pocket-hole-joinery/pocket-hole-jigs/kreg-pocket-hole-jig-720pro/KPHJ720PRO.html",
            "category": "woodworking",
        },
        {
            "title": "Use cases with Langchain",
            "summary": "This article discusses various use cases of Langchain, highlighting its applications in building complex, chainable workflows for data processing, machine learning, and automation.",
            "url": "https://medium.com/@ebruboyaci35/use-cases-with-langchain-e0fd5b0587f1",
            "category": "programming",
        },
        {
            "title": "Code Understanding",
            "summary": "This resource explores tools and techniques for understanding and analyzing code, focusing on improving code readability, maintainability, and debugging efficiency.",
            "url": "https://python.langchain.com/docs/use_cases/code_understanding",
            "category": "programming",
        },
        {
            "title": "What is ChatGPT Code Interpreter and how do you use it?",
            "summary": "The ChatGPT Code Interpreter is a tool that allows ChatGPT to run and interpret code, enabling users to execute scripts, analyze data, and automate tasks within a conversational interface.",
            "url": "https://www.geeky-gadgets.com/chatgpt-code-interpreter/",
            "category": "programming",
        },
        {
            "title": "Awesome List of the Best Developer Tools",
            "summary": "This article provides a curated list of the best tools for developers, including code editors, version control systems, and productivity tools, aimed at enhancing development workflows.",
            "url": "https://dev.to/surajondev/awesome-list-of-the-best-developer-tools-12fp",
            "category": "programming",
        },
        {
            "title": 'Using "any" and "all" in Python',
            "summary": '"Any" and "all" are built-in Python functions used to evaluate iterables. "Any" returns True if at least one element is True, while "all" returns True only if all elements are True.',
            "url": "https://www.pythonmorsels.com/any-and-all/",
            "category": "programming",
        },
        {
            "title": "What is a context manager",
            "summary": "A context manager in Python is a construct that allows for the setup and cleanup of resources, ensuring proper management through the use of 'with' statements. It is commonly used for handling file operations, network connections, and locks.",
            "url": "https://www.pythonmorsels.com/what-is-a-context-manager/",
            "category": "programming",
        },
        {
            "title": "zipapp — Manage executable Python zip archives",
            "summary": "Zipapp is a Python module for creating and managing executable zip archives. It allows bundling Python applications into single-file executables for easier distribution and deployment.",
            "url": "https://docs.python.org/3/library/zipapp.html",
            "category": "programming",
        },
        {
            "title": "pytest-benchmark",
            "summary": "Pytest-benchmark is a plugin for pytest that helps measure and compare code performance, aiding in identifying bottlenecks and optimizing applications.",
            "url": "https://pypi.org/project/pytest-benchmark/",
            "category": "programming",
        },
        {
            "title": "Github Copilot Extensions",
            "summary": "GitHub introduces Copilot Extensions, enhancing the AI developer tool by integrating partner services like DataStax, Docker, and Azure. These extensions allow developers to stay in their flow by accessing tools and services directly within their IDE or GitHub.com. They support natural language interactions for tasks like troubleshooting and deployment. The marketplace offers both public and private extensions, enabling customized developer workflows.",
            "url": "https://github.blog/2024-05-21-introducing-github-copilot-extensions/",
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
            logger.critical(thing)
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
        for _ in tqdm(range(2), desc="creating demo posts", leave=False):
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
