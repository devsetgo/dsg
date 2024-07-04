# -*- coding: utf-8 -*-
import re

from dsg_lib.async_database_functions import base_schema
from loguru import logger
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    event,
)
from sqlalchemy.orm import class_mapper, relationship

from .db_init import async_db
from .functions.encrypt import (
    DecryptionError,
    EncryptionError,
    decrypt_text,
    encrypt_text,
)
from .settings import settings

if settings.db_driver.startswith("sqlite"):
    schema_base = base_schema.SchemaBaseSQLite
elif settings.db_driver.startswith("postgres"):
    schema_base = base_schema.SchemaBasePostgres
else:
    raise ValueError("Untested database driver")


class Users(schema_base, async_db.Base):
    __tablename__ = "users"  # Name of the table in the database
    __tableargs__ = {"comment": "Users of the application"}

    # Define the columns of the table
    first_name = Column(String, unique=False, index=True)  # First name of the user
    last_name = Column(String, unique=False, index=True)  # Last name of the user
    user_name = Column(
        String, unique=True, index=True, nullable=False
    )  # Last name of the user
    email = Column(
        String, unique=False, index=True, nullable=True
    )  # Email of the user, must be unique
    # password = Column(
    #     String, unique=False, index=True, nullable=False
    # )  # Password of the user
    provider = Column(String, unique=False)
    # timezone of the user, should default to new york
    my_timezone = Column(String, unique=False, index=True, default="America/New_York")
    is_active = Column(Boolean, default=True, nullable=False)  # If the user is active
    is_admin = Column(Boolean, default=False, nullable=False)  # If the user is an admin
    update_by = Column(
        String, unique=False, index=True
    )  # Last user to update the record
    # site_access = Column(
    #     Boolean, default=False, nullable=False
    # )  # If the user has access to the site
    date_last_login = Column(DateTime, unique=False, index=True)  # Last login date
    failed_login_attempts = Column(Integer, default=0)  # Failed login attempts
    is_locked = Column(
        Boolean, default=False, index=True, nullable=False
    )  # If the user account is locked
    roles = Column(JSON, default={})  # Roles of the user
    removal_flag = Column(DateTime, index=True)  # Removal flag

    # combine first and last name into a full name
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }

    # Define the child relationship to the InterestingThings class

    interesting_things = relationship(
        "InterestingThings", back_populates="users", cascade="all,delete"
    )
    posts = relationship("Posts", back_populates="user", cascade="all,delete")
    categories = relationship(
        "Categories", back_populates="users", cascade="all,delete"
    )
    notes = relationship("Notes", back_populates="users", cascade="all,delete")
    note_metrics = relationship(
        "NoteMetrics", back_populates="users", cascade="all,delete"
    )
    job_applications = relationship(
        "JobApplications", back_populates="users", cascade="all,delete"
    )


class FailedLoginAttempts(schema_base, async_db.Base):
    __tablename__ = "failed_login_attempts"  # Name of the table in the database
    __tableargs__ = {"comment": "Failed login attempts for the users"}

    # Define the columns of the table
    user_name = Column(String, unique=False, index=True)
    password = Column(String, unique=False, index=True)
    real_id = Column(Boolean, default=False, index=True)
    meta_data = Column(JSON)

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


class Posts(schema_base, async_db.Base):
    __tablename__ = "posts"

    title = Column(String(200), nullable=False)
    summary = Column(String(1000), index=True)
    content = Column(Text, nullable=False)  # Stores the HTML or Markdown text
    category = Column(String, unique=False, index=True)  # category of item
    tags = Column(JSON)
    ai_fix = Column(Boolean, default=False)
    word_count = Column(Integer)
    user_id = Column(
        String, ForeignKey("users.pkid"), unique=False, index=True
    )  # Foreign key to the Users table
    # Define the parent relationship to the Users class
    user = relationship("Users", back_populates="posts")

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


@event.listens_for(Posts, "before_insert")
@event.listens_for(Posts, "before_update")
def posts_on_change(mapper, connection, target):
    target.word_count = len(target.content.split())

    pattern = re.compile("[^a-zA-Z, ]")
    target.ai_fix = False  # Set ai_fix to False by default
    for tag in target.tags:
        if pattern.search(tag) or " " in tag:
            target.ai_fix = (
                True  # Set ai_fix to True only if an illegal character is found
            )
            break


class InterestingThings(schema_base, async_db.Base):
    __tablename__ = "interesting_things"  # Name of the table in the database
    __tableargs__ = {"comment": "Interesting things that the user finds"}

    # Define the columns of the table
    title = Column(String, unique=False, index=True)  # name of item
    summary = Column(String, unique=False, index=True)  # description of item
    url = Column(String, unique=False, index=True)  # url of item
    category = Column(String, unique=False, index=True)  # category of item
    public = Column(Boolean, default=False)  # If the item is public
    # Define the parent relationship to the User class
    user_id = Column(String, ForeignKey("users.pkid"))  # Foreign key to the User table
    users = relationship(
        "Users", back_populates="interesting_things"
    )  # Relationship to the Users class

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


class Categories(schema_base, async_db.Base):
    __tablename__ = "categories"  # Name of the table in the database
    __tableargs__ = {"comment": "Categories of interesting things"}

    # Define the columns of the table
    name = Column(String(50), unique=False, index=True)  # name of item
    description = Column(String(500), unique=False, index=True)  # description of item
    is_post = Column(Boolean, default=False, index=True)
    is_thing = Column(Boolean, default=False, index=True)
    is_system = Column(
        Boolean, default=True, index=True
    )  # If the category is a system default
    user_id = Column(String, ForeignKey("users.pkid"))
    users = relationship("Users", back_populates="categories")

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


class NoteMetrics(schema_base, async_db.Base):
    __tablename__ = "note_metrics"

    user_id = Column(
        String, ForeignKey("users.pkid"), nullable=False, index=True, unique=True
    )
    word_count = Column(Integer, default=0)
    character_count = Column(Integer, default=0)
    note_count = Column(Integer, default=0)
    mood_metric = Column(JSON)
    metrics = Column(JSON)

    total_unique_tag_count = Column(Integer, default=0)
    users = relationship("Users", back_populates="note_metrics")

    def to_dict(self):
        data = {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }
        return data


class Notes(schema_base, async_db.Base):
    __tablename__ = "notes"
    __tableargs__ = {"comment": "Notes that the user writes"}

    mood = Column(String(500), unique=False, index=True)
    mood_analysis = Column(String(500), unique=False, index=True)
    _note = Column(Text, unique=False, index=True, nullable=False)
    tags = Column(JSON)
    _summary = Column(String(500), unique=False, index=True)
    word_count = Column(Integer)
    character_count = Column(Integer)
    ai_fix = Column(Boolean, default=False)
    user_id = Column(String, ForeignKey("users.pkid"), nullable=False, index=True)
    users = relationship("Users", back_populates="notes")

    # def __init__(self, note):
    #     self._note = encrypt_text(note)  # Encrypt and store the note internally

    def to_dict(self):
        data = {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }
        data["note"] = self.note  # Add the decrypted note
        data["summary"] = self.summary
        return data

    @property
    def note(self):
        try:
            return decrypt_text(self._note)
        except DecryptionError as e:
            error:str = f"Failed to decrypt note: {e}"
            logger.error(error)
            # Decide on the action: raise, ignore, or another approach
            return error

    @note.setter
    def note(self, value):
        try:
            self._note = encrypt_text(value)
        except EncryptionError as e:
            error:str = f'Failed to encrypt note: {e}'
            logger.error(error)
            # Decide on the action: raise, ignore, or another approach
            return error

    @property
    def summary(self):
        try:
            return decrypt_text(self._summary)
        except DecryptionError as e:
            error:str = f"Failed to decrypt summary: {e}"
            logger.error(error)
            # Decide on the action: raise, ignore, or another approach
            return error

    @summary.setter
    def summary(self, value):
        try:
            self._summary = encrypt_text(value)
        except EncryptionError as e:
            error:str = f"Failed to encrypt summary: {e}"
            logger.error(error)
            # Decide on the action: raise, ignore, or another approach
            return error


@event.listens_for(Notes, "before_insert")
@event.listens_for(Notes, "before_update")
def note_on_change(mapper, connection, target):
    target.word_count = len(target.note.split())
    target.character_count = len(target.note)

    pattern = re.compile("[^a-zA-Z, ]")
    target.ai_fix = False  # Set ai_fix to False by default

    # Check if mood is not one of the specified values
    if target.mood not in ["positive", "negative", "neutral"]:
        target.ai_fix = True

    # Check if mood_analysis is more than one word
    if " " in target.mood_analysis:
        target.ai_fix = True

    for tag in target.tags:
        if pattern.search(tag) or " " in tag:
            target.ai_fix = True  # Set ai_fix to True if an illegal character is found
            break

    # if target.note:  # Check if the note is not None
    #     target.note = encrypt_text(target.note)


class LibraryName(async_db.Base):
    __tablename__ = "library_names"
    __tableargs__ = {"comment": "Stores unique library names"}
    pkid = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Library(schema_base, async_db.Base):
    __tablename__ = "libraries"
    __tableargs__ = {
        "comment": "Stores library data including current and new versions"
    }
    request_group_id = Column(String, index=True)
    library_id = Column(Integer, ForeignKey("library_names.pkid"))
    library = relationship("LibraryName")
    current_version = Column(String, index=True)
    new_version = Column(String, index=True)
    new_version_vulnerability = Column(Boolean, default=False, index=True)
    vulnerability = Column(JSON)

    def to_dict(self):
        data = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        data["library_name"] = self.library.name
        return data


class Requirement(schema_base, async_db.Base):
    __tablename__ = "requirements"
    __tableargs__ = {
        "comment": "Stores requirement data including input text and JSON data"
    }
    request_group_id = Column(String, unique=True, index=True)
    text_in = Column(String)
    json_data_in = Column(JSON)
    json_data_out = Column(JSON)
    lib_out_count = Column(Integer)
    lib_in_count = Column(Integer)
    host_ip = Column(String, index=True)
    header_data = Column(JSON)
    user_agent = Column(String)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class JobApplications(schema_base, async_db.Base):
    __tablename__ = "job_applications"  # Name of the table in the database
    __tableargs__ = {"comment": "Job applications that the user has submitted"}

    # Define the columns of the table
    url = Column(String, unique=False, index=True)  # URL of the job posting
    job_title = Column(String, unique=False, index=True)  # Job title
    company_name = Column(String, unique=False, index=True)  # Company name
    application_date = Column(DateTime, unique=False, index=True)  # Application date
    application_status = Column(String, unique=False, index=True)  # Application status
    user_id = Column(String, ForeignKey("users.pkid"))  # Foreign key to the User table

    # Define the parent relationship to the User class
    users = relationship("Users", back_populates="job_applications")

    # Define the child relationship to the JobApplicationTasks class
    tasks = relationship("JobApplicationTasks", back_populates="job_application")

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


class JobApplicationTasks(schema_base, async_db.Base):
    __tablename__ = "job_application_tasks"  # Name of the table in the database
    __tableargs__ = {"comment": "Tasks related to a job application"}

    # Define the columns of the table
    task_description = Column(String, unique=False, index=True)  # Task description
    due_date = Column(DateTime, unique=False, index=True)  # Due date for the task
    status = Column(String, unique=False, index=True)  # Status of the task
    job_application_id = Column(
        String, ForeignKey("job_applications.pkid")
    )  # Foreign key to the JobApplications table

    # Define the parent relationship to the JobApplications class
    job_application = relationship("JobApplications", back_populates="tasks")

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }
