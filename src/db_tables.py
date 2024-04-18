# -*- coding: utf-8 -*-

from dsg_lib.async_database_functions import base_schema
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import class_mapper, relationship

from .db_init import async_db
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
    user_name = Column(String, unique=True, index=True)  # Last name of the user
    email = Column(
        String, unique=False, index=True, nullable=True
    )  # Email of the user, must be unique
    password = Column(String, unique=False, index=True)  # Password of the user
    # timezone of the user, should default to new york
    my_timezone = Column(String, unique=False, index=True, default="America/New_York")
    is_active = Column(Boolean, default=True)  # If the user is active
    is_admin = Column(Boolean, default=False)  # If the user is an admin
    site_access = Column(Boolean, default=False)  # If the user has access to the site
    date_last_login = Column(DateTime, unique=False, index=True)  # Last login date
    failed_login_attempts = Column(Integer, default=0)  # Failed login attempts
    is_locked = Column(Boolean, default=False)  # If the user account is locked

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
    categories = relationship(
        "Categories", back_populates="users", cascade="all,delete"
    )
    notes = relationship("Notes", back_populates="users", cascade="all,delete")
    job_applications = relationship(
        "JobApplications", back_populates="users", cascade="all,delete"
    )


class InterestingThings(schema_base, async_db.Base):
    __tablename__ = "interesting_things"  # Name of the table in the database
    __tableargs__ = {"comment": "Interesting things that the user finds"}

    # Define the columns of the table
    name = Column(String, unique=False, index=True)  # name of item
    description = Column(String, unique=False, index=True)  # description of item
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
    is_system = Column(Boolean, default=True)  # If the category is a system default
    is_active = Column(Boolean, default=True)  # If the c   ategory is active
    user_id = Column(String, ForeignKey("users.pkid"))
    users = relationship("Users", back_populates="categories")

    def to_dict(self):
        return {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }


class Notes(schema_base, async_db.Base):
    __tablename__ = "notes"  # Name of the table in the database
    __tableargs__ = {"comment": "Notes that the user writes"}

    # Define the columns of the table
    mood = Column(String(50), unique=False, index=True)  # mood of note
    mood_analysis = Column(String(50), unique=False, index=True)  # mood of note
    note = Column(Text, unique=False, index=True)  # note
    tags = Column(JSON)  # tags from OpenAI
    summary = Column(String(100), unique=False, index=True)  # summary from OpenAI
    # Define the parent relationship to the User class
    user_id = Column(String, ForeignKey("users.pkid"))  # Foreign key to the User table
    users = relationship("Users", back_populates="notes")

    @property
    def word_count(self):
        return len(self.note.split())

    @property
    def character_count(self):
        return len(self.note)

    def to_dict(self):
        data = {
            c.key: getattr(self, c.key) for c in class_mapper(self.__class__).columns
        }
        data["word_count"] = self.word_count
        data["character_count"] = self.character_count
        return data


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
