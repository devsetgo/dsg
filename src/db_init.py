# -*- coding: utf-8 -*-
"""
This module, `db_init.py`, is responsible for initializing the database connection for a FastAPI application. It dynamically constructs the database URI based on the application's configuration settings, supporting various database drivers such as SQLite (with aiosqlite for asynchronous support), PostgreSQL, MySQL, Oracle, and MSSQL. The module also defines a mapping of configuration options to database drivers, indicating which options are supported by each driver.

The database URI construction takes into account different scenarios, including in-memory SQLite databases, file-based SQLite databases, and other SQL databases requiring connection details such as username, password, host, and port.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - dsg_lib.async_database_functions: Provides asynchronous database functions and configuration utilities.
    - loguru: Used for logging.
    - .settings: A module containing the application's configuration settings, including database connection details.

Functions:
    None explicitly defined; the module's main functionality is executed at the module level during import, setting up the database URI based on the application's configuration.

Usage:
    This module is intended to be imported at the application startup to ensure the database connection is configured correctly. It automatically constructs the database URI from the application settings and logs it for debugging purposes.
"""
from dsg_lib.async_database_functions import async_database, database_config
from loguru import logger

from .settings import settings

if str(settings.db_driver.value).startswith(
    "sqlite+aiosqlite:///:memory:?cache=shared"
):
    db_uri: str = settings.db_driver.value
elif settings.db_driver.value == "sqlite+aiosqlite":
    db_name = settings.db_name.get_secret_value()
    if "." not in db_name:
        db_name = f"{db_name}.db"
    db_uri: str = f"{settings.db_driver.value}:///sqlite_db/{db_name}"
else:
    db_username = settings.db_username.get_secret_value()
    db_password = settings.db_password.get_secret_value()
    db_name = settings.db_name.get_secret_value()
    db_port = settings.db_port
    # postgresql://username:password@localhost:5432/mydatabase
    db_uri: str = (
        f"{settings.db_driver.value}://{db_username}:{db_password}@{settings.db_host}:{settings.db_port}/{db_name}"
    )
logger.debug(f"{db_uri}")


# Mapping of configuration options to database drivers that support them
option_support = {
    "echo": ["sqlite+aiosqlite", "postgresql", "mysql", "oracle", "mssql"],
    "future": ["sqlite+aiosqlite", "postgresql", "mysql", "oracle", "mssql"],
    "pool_pre_ping": ["postgresql", "mysql", "oracle", "mssql"],
    "pool_size": ["postgresql", "mysql", "oracle", "mssql"],
    "max_overflow": ["postgresql", "mysql", "oracle", "mssql"],
    "pool_recycle": ["sqlite+aiosqlite", "postgresql", "mysql", "oracle", "mssql"],
    "pool_timeout": ["postgresql", "mysql", "oracle", "mssql"],
}

config = {"database_uri": db_uri}

# Check each option
for option in [
    "echo",
    "future",
    "pool_pre_ping",
    "pool_size",
    "max_overflow",
    "pool_recycle",
    "pool_timeout",
]:
    value = getattr(settings, option)
    # Check if the driver string starts with a supported driver
    for driver in option_support[option]:
        if settings.db_driver.value.startswith(driver) and value is not None:
            config[option] = value
            break

logger.debug(f"database config: {config}")
logger.info("setting up database")
db_config = database_config.DBConfig(config)
async_db = async_database.AsyncDatabase(db_config)
"""
function              SQLite  PostgreSQL  MySQL  Oracle  MSSQL
echo (bool)           Yes     Yes         Yes    Yes     Yes
future (bool)         Yes     Yes         Yes    Yes     Yes
pool_pre_ping (bool)  No     Yes         Yes    Yes     Yes
pool_size (int)       No      Yes         Yes    Yes     Yes
max_overflow (int)    No      Yes         Yes    Yes     Yes
pool_recycle (bool)   Yes     Yes         Yes    Yes     Yes
pool_timeout (int)    No      Yes         Yes    Yes     Yes
"""
