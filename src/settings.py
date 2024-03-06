# -*- coding: utf-8 -*-

"""
This module provides classes and functions for managing database settings in an
application.
"""
import secrets  # For generating secure random numbers
from datetime import datetime  # A Python library used for working with dates and times
from enum import (
    Enum,  # For creating enumerations, which are a set of symbolic names bound to unique constant values
)
from functools import lru_cache  # For caching the results of expensive function calls
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union,
)

from loguru import logger  # For logging
from pydantic import (  # For validating data
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    ValidationInfo,
    field_validator,
    model_validator,
    root_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class SameSiteEnum(str, Enum):
    Lax = "Lax"
    Strict = "Strict"
    None_ = "None"


class DatabaseDriverEnum(str, Enum):
    postgres = "postgresql+asyncpg"
    sqlite = "sqlite+aiosqlite"
    memory = "sqlite+aiosqlite:///:memory:?cache=shared"
    mysql = "mysql+aiomysql"
    oracle = "oracle+cx_oracle"

    model_config = ConfigDict(use_enum_values=True, extra="allow")


class Settings(BaseSettings):
    # Class that describes the settings schema
    # database_configuration: DatabaseSettings = DatabaseSettings()
    db_driver: DatabaseDriverEnum = Field("memory", description="DB_DRIVER")
    db_username: SecretStr = Field(..., description="DB_USERNAME")
    db_password: SecretStr = Field(..., description="DB_PASSWORD")
    db_host: str = Field(..., description="DB_HOST")
    db_port: int = Field(..., description="DB_PORT")
    db_name: SecretStr = Field(
        ..., description="For sqlite it should be folder path 'folder/filename"
    )
    echo: bool = Field(True, description="Enable echo")
    future: bool = Field(True, description="Enable future")
    pool_pre_ping: bool = Field(False, description="Enable pool_pre_ping")
    pool_size: Optional[int] = Field(None, description="Set pool_size")
    max_overflow: Optional[int] = Field(None, description="Set max_overflow")
    pool_recycle: int = Field(3600, description="Set pool_recycle")
    pool_timeout: Optional[int] = Field(None, description="Set pool_timeout")

    # Generate a random secret key
    csrf_secret: str = secrets.token_hex(32)
    # Set the current date and time when the application is run
    date_run: datetime = datetime.utcnow()
    # application settings
    release_env: str = "prd"
    debug_mode: bool = False
    # logging settings
    logging_directory: str = "log"
    log_name: str = "log.log"
    logging_level: str = "INFO"
    log_rotation: str = "100 MB"
    log_retention: str = "30 days"
    log_backtrace: bool = False
    log_serializer: bool = False
    log_diagnose: bool = False
    # session management
    max_failed_login_attempts: int = 5
    session_secret_key: str = secrets.token_hex(32)  # Generate a random secret key
    same_site: SameSiteEnum = Field("Lax", description="Options: Lax, Strict, None")
    https_only: bool = False
    max_age: int = 3600
    sesson_user_identifier: str = "user_identifier"
    # service accounts
    openai_key: SecretStr = None  # OpenAI API Key
    # GitHub
    github_id: str = "octocat"
    github_repo_limit: int = 50
    github_token: SecretStr = "<enter key>"

    # add an admin user
    create_admin_user: bool = False
    admin_user: SecretStr = None
    admin_password: SecretStr = None
    # create psuedo data
    create_demo_user: bool = False
    create_base_categories: bool = False
    create_demo_data: bool = False

    @root_validator(pre=True)
    def parse_database_driver(cls, values):
        db_driver = values.get("db_driver")
        if isinstance(db_driver, str):
            try:
                values["db_driver"] = DatabaseDriverEnum[db_driver].value
            except KeyError:
                pass
        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow",
        # use_enum_values=True
    )  # Set up the configuration dictionary for the settings


@lru_cache
def get_settings():
    # Function to get an instance of the Settings class. The results are cached
    # to improve performance.
    logger.debug(f"Settings: {Settings().dict()}")
    return Settings()


settings = get_settings()  # Get the settings


# config = {
#     "database_uri": "sqlite+aiosqlite:///:memory:?cache=shared",
#     "echo": True,
#     "future": True,
#     "pool_pre_ping": False,
#     "pool_size":None,
#     "max_overflow": None,
#     "pool_recycle": 3600,
#     "pool_timeout": None,
# }


# class DatabaseDriverEnum(str, Enum): # Enum class to hold database driver
#     values. It inherits both str and Enum classes.

#     postgres = "postgresql+asyncpg" sqlite = "sqlite+aiosqlite" memory =
#     "sqlite+aiosqlite:///:memory:?cache=shared" mysql = "mysql+aiomysql"
#     oracle = "oracle+cx_oracle"

#     model_config = ConfigDict( use_enum_values=True )  # Configuration
#         dictionary to use enum values


# db_user: str = None db_password: str = None db_host: str = None db_port: int =
# 5432 db_name: str = None


# def database_uri(self) -> str: # Method to generate the appropriate database
#     URI based on the selected driver if self.database_driver ==
#     DatabaseDriverEnum.memory: return str(self.database_driver) elif
#         self.database_driver == DatabaseDriverEnum.sqlite: # For SQLite, only
#     the database name is required. return
#         f"{self.database_driver}:///{self.db_name}.db" else: return
#         f"{self.database_driver}://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

# def dict(self): # Method to convert the settings object into a dictionary
#     original_dict = super().dict() original_dict.update( {"database_uri":
#     self.database_uri()} )  # Add the database_uri to the dictionary return
#     original_dict

# @field_validator("database_driver", mode="before") @classmethod def
# parse_database_driver(cls, value): """ Validator method to convert the input
# string to the corresponding enum member value.

#     Args: value (str): The input string to be converted.

#     Returns:
#         The corresponding enum member value if the input string is valid, otherwise returns the input value.
#     """
#     if isinstance(value, str):
#         try:
#             return DatabaseDriverEnum[value]
#         except KeyError:
#             pass
#     return value
# Define fields with default values database_driver: DatabaseDriverEnum  # Use
# the DatabaseDriverEnum Enum for DB_TYPE
