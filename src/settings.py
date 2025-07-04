# -*- coding: utf-8 -*-
"""
This module, `settings.py`, defines the configuration schema for the application using Pydantic models. It includes settings for database connections, supporting multiple database drivers such as PostgreSQL, SQLite, MySQL, and Oracle. The module leverages Pydantic's BaseSettings class to automatically load environment variables and validate them against the defined schema, ensuring that the application starts with a valid configuration.

The `Settings` class within this module specifies the structure of the application's configuration, including database connection details (driver, username, password, host, port, and database name) and other application-specific settings as needed. It also defines enums for database drivers and cookie SameSite policies to ensure that only valid options are used throughout the application.

Author:
    Mike Ryan

License:
    MIT License

Dependencies:
    - pydantic: For data validation and settings management.
    - loguru: For logging.
    - secrets, datetime, enum, functools: Standard library modules for security, date handling, enumerations, and caching.

Classes:
    - SameSiteEnum: Enumerates valid options for the SameSite attribute of cookies.
    - DatabaseDriverEnum: Enumerates supported database drivers and their connection strings.
    - Settings: Defines the application's configuration schema, including database connection details and other necessary settings.

Usage:
    This module is intended to be imported and instantiated at the application startup to configure and validate the application settings. The `Settings` instance can then be used throughout the application to access configuration values.
"""
import secrets  # For generating secure random numbers
from datetime import datetime  # A Python library used for working with dates and times
from enum import (
    Enum,  # For creating enumerations, which are a set of symbolic names bound to unique constant values
)
from functools import lru_cache  # For caching the results of expensive function calls
from typing import Optional

from loguru import logger  # For logging
from pydantic import (  # For validating data
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from . import __version__


class SameSiteEnum(str, Enum):
    Lax = "Lax"
    Strict = "Strict"
    None_ = "None"


class DatabaseDriverEnum(str, Enum):
    postgres = "postgresql+asyncpg"
    postgresql = "postgresql+asyncpg"
    sqlite = "sqlite+aiosqlite"
    memory = "sqlite+aiosqlite:///:memory:?cache=shared"
    # mysql = "mysql+aiomysql"
    # oracle = "oracle+cx_oracle"

    model_config = ConfigDict(use_enum_values=True, extra="allow")


class Settings(BaseSettings):
    # Class that describes the settings schema
    https_redirect: bool = False
    # allowed_hosts: list = ["localhost", "devsetgo.com","*.devsetgo.com","0.0.0.0"]
    # database_configuration: DatabaseSettings = DatabaseSettings()
    db_driver: DatabaseDriverEnum = Field("memory", description="DB_DRIVER")
    db_username: SecretStr = Field(..., description="DB_USERNAME")
    db_password: SecretStr = Field(..., description="DB_PASSWORD")
    db_host: str = Field(..., description="DB_HOST")
    db_port: int = Field(..., description="DB_PORT")
    db_name: SecretStr = Field(
        ..., description="For sqlite it should be folder path 'folder/filename"
    )
    phrase: SecretStr = Field(..., description="substitution cipher")
    salt: SecretStr = Field(..., description="salt for key derivation")
    echo: bool = Field(True, description="Enable echo")
    future: bool = Field(True, description="Enable future")
    pool_pre_ping: bool = Field(False, description="Enable pool_pre_ping")
    pool_size: Optional[int] = Field(None, description="Set pool_size")
    max_overflow: Optional[int] = Field(None, description="Set max_overflow")
    pool_recycle: int = Field(3600, description="Set pool_recycle")
    pool_timeout: Optional[int] = Field(None, description="Set pool_timeout")

    # Set the current date and time when the application is run
    date_run: datetime = datetime.utcnow()
    # application settings
    release_env: str = "prd"
    version: str = __version__
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
    log_intercept_standard_logging: bool = False
    # session management
    max_failed_login_attempts: int = 5
    session_secret_key: str = secrets.token_hex(32)  # Generate a random secret key
    same_site: SameSiteEnum = Field("Lax", description="Options: Lax, Strict, None")
    https_only: bool = False
    max_age: int = 3600
    session_user_identifier: str = "user_identifier"
    # service accounts
    # OpenAI Settings
    open_ai_disabled: bool = False
    openai_key: SecretStr = None  # OpenAI API Key
    openai_model: str = "gpt-3.5-turbo-1106"
    mood_analysis_weights: list = [
        ("elated", 1),
        ("overjoyed", 0.875),
        ("ecstatic", 0.75),
        ("joyful", 0.625),
        ("happy", 0.5),
        ("pleased", 0.375),
        ("content", 0.25),
        ("neutral", 0),
        ("concerned", -0.25),
        ("disappointed", -0.375),
        ("sad", -0.5),
        ("upset", -0.625),
        ("angry", -0.75),
        ("despair", -0.875),
        ("hopeless", -1),
    ]

    # GitHub
    github_client_id: str = None
    github_client_secret: SecretStr = None
    github_call_back_domain: str = "https://localhost:5000"
    github_id: str = "octocat"
    github_repo_limit: int = 50
    github_token: SecretStr = "<enter key>"
    # historical data
    history_range: int = 1
    # add an admin user
    create_admin_user: bool = False
    admin_user: SecretStr = None
    admin_password: SecretStr = None
    admin_email: EmailStr = None
    default_timezone: str = "America/New_York"
    # create psuedo data
    create_demo_user: bool = False
    create_demo_users_qty: int = 0
    create_base_categories: bool = False
    create_demo_data: bool = False
    create_demo_notes: bool = False
    create_demo_notes_qty: int = 0
    create_demo_posts: bool = False
    create_demo_posts_qty: int = 0

    convert_markdown_to_html: bool = False

    @model_validator(mode="before")
    @classmethod
    def parse_database_driver(cls, values):
        db_driver = values.get("db_driver")
        if isinstance(db_driver, str):
            try:
                # Convert db_driver to lower case before getting its value from the enum
                values["db_driver"] = DatabaseDriverEnum[db_driver.lower()].value
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
    logger.debug(f"Settings: {Settings().model_dump()}")
    return Settings()


settings = get_settings()  # Get the settings
