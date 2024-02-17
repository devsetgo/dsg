# -*- coding: utf-8 -*-
from dsg_lib.async_database_functions import async_database, database_config
from loguru import logger

from .settings import settings

if settings.db_driver.value == "sqlite+aiosqlite:///:memory:?cache=shared":
    db_uri: str = settings.db_driver.value
elif settings.db_driver.value == "sqlite+aiosqlite":
    db_name = settings.db_name.get_secret_value()
    if "." not in db_name:
        db_name = f"{db_name}.db"
    db_uri: str = f"{settings.db_driver.value}:///{db_name}"
else:
    db_username = settings.db_username.get_secret_value()
    db_password = settings.db_password.get_secret_value()
    db_name = settings.db_name.get_secret_value()
    # postgresql://username:password@localhost:5432/mydatabase
    db_uri: str = (
        f"{settings.db_driver.value}://{db_username}:{db_password}@{settings.db_host}:{settings.db_port}/{db_name}"
    )

logger.debug(db_uri)

config = {
    "database_uri": db_uri,
    "echo": False,
    "future": True,
    # "pool_pre_ping": False, # not suppport in sqlite
    # "pool_size": None, # not suppport in sqlite
    # "max_overflow": None, # not suppport in sqlite
    "pool_recycle": 3600,
    # "pool_timeout": None, # not suppport in sqlite
}

logger.info("setting up database")
db_config = database_config.DBConfig(config)
async_db = async_database.AsyncDatabase(db_config)


"""
function              SQLite  PostgreSQL  MySQL  Oracle  MSSQL
echo (bool)           Yes     Yes         Yes    Yes     Yes
future (bool)         Yes     Yes         Yes    Yes     Yes
pool_pre_ping (bool)  Yes     Yes         Yes    Yes     Yes
pool_size (int)       No      Yes         Yes    Yes     Yes
max_overflow (int)    No      Yes         Yes    Yes     Yes
pool_recycle (bool)   Yes     Yes         Yes    Yes     Yes
pool_timeout (int)    No      Yes         Yes    Yes     Yes
"""
