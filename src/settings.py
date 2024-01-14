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

from pydantic import (  # For validating data
    ConfigDict,
    Field,
    field_validator,
    validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class SameSiteEnum(str, Enum):
    Lax = "Lax"
    Strict = "Strict"
    None_ = "None"


class Settings(BaseSettings):
    # Class that describes the settings schema
    csrf_secret: str = secrets.token_hex(128)  # Generate a random secret key
    date_run: datetime = (
        datetime.utcnow()
    )  # Set the current date and time when the application is run
    # application settings
    release_env: str = "prd"
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
    session_secret_key: str = secrets.token_hex(128)  # Generate a random secret key
    same_site: SameSiteEnum = Field("Lax", description="Options: Lax, Strict, None")
    https_only: bool = False
    max_age: int = 3600
    # service accounts
    openai_key: str = None  # OpenAI API Key
    # GitHub
    github_id: str = "octocat"
    github_repo_limit: int = 20
    github_token: str = "<enter key>"
    
    # add an admin user
    create_admin_user: bool = False
    admin_user: str = None
    admin_password: str = None


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        # use_enum_values=True
    )  # Set up the configuration dictionary for the settings


@lru_cache
def get_settings():
    # Function to get an instance of the Settings class. The results are cached
    # to improve performance.
    return Settings()


settings = get_settings()  # Get the settings


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
