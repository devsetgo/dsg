from dsg_lib import async_database, database_config
from loguru import logger

config = {
    "database_uri": "sqlite+aiosqlite:///:memory:?cache=shared",
    "echo": False,
    "future": True,
    "pool_recycle": 3600,
}

logger.info("setting up database")
db_config = database_config.DBConfig(config)
async_db = async_database.AsyncDatabase(db_config)
