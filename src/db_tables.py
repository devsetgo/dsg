import openai
from dsg_lib import base_schema
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship
from .functions.ai import get_tags, get_summary

from .db_init import async_db


class User(base_schema.SchemaBase, async_db.Base):
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
    is_active = Column(Boolean, default=True)  # If the user is active
    is_admin = Column(Boolean, default=False)  # If the user is an admin

    # combine first and last name into a full name
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    # Define the child relationship to the InterestingThings class
    InterestingThings = relationship(
        "InterestingThings", back_populates="user"
    )  # Relationship to the InterestingThings class
    # Define the child relationship to the Categories class
    Categories = relationship(
        "Categories", back_populates="user"
    )  # Relationship to the Categories class
    # Define the child relationship to the Notes class
    Notes = relationship(
        "Notes", back_populates="user"
    )  # Relationship to the Notes class


class InterestingThings(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "interesting_things"  # Name of the table in the database
    __tableargs__ = {"comment": "Interesting things that the user finds"}

    # Define the columns of the table
    name = Column(String, unique=False, index=True)  # name of item
    description = Column(String, unique=False, index=True)  # description of item
    url = Column(String, unique=False, index=True)  # url of item
    category = Column(String, unique=False, index=True)  # category of item
    # Define the parent relationship to the User class
    user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
    user = relationship(
        "User", back_populates="InterestingThings"
    )  # Relationship to the User class


class Categories(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "categories"  # Name of the table in the database
    __tableargs__ = {"comment": "Categories of interesting things"}

    # Define the columns of the table
    name = Column(String(50), unique=False, index=True)  # name of item
    description = Column(String(500), unique=False, index=True)  # description of item
    is_system = Column(Boolean, default=True)  # If the category is a system default
    is_active = Column(Boolean, default=True)  # If the category is active
    # Define the parent relationship to the User class
    user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
    user = relationship(
        "User", back_populates="Categories"
    )  # Relationship to the User class



class Notes(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "notes"  # Name of the table in the database
    __tableargs__ = {"comment": "Notes that the user writes"}

    # Define the columns of the table
    mood = Column(String(50), unique=False, index=True)  # mood of note
    note = Column(String(500), unique=False, index=True)  # note
    tags = Column(JSON)  # tags from OpenAI
    summary = Column(String(500), unique=False, index=True)  # summary from OpenAI
    # Define the parent relationship to the User class
    user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
    user = relationship(
        "User", back_populates="Notes"
    )  # Relationship to the User class

    @property
    def word_count(self):
        return len(self.note.split())

    @property
    def character_count(self):
        return len(self.note)



class Requirements(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "requirements"  # Name of the table in the database
    __tableargs__ = {"comment": "Requirements that the user writes"}

    # Define the columns of the table
    text_in = Column(String(5000), unique=False, index=True)  # text_in
    json_data_in = Column(JSON)  # json_data_in
    json_data_out = Column(JSON)  # json_data_out
    lib_out_count = Column(Integer)  # lib_out_count
    host_ip = Column(String(50), unique=False, index=True)  # host_ip
    header_data = Column(JSON)  # header_data
    private = Column(Boolean, default=False)  # If the note is private
    # Define the parent relationship to the User class
    # user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
    # user = relationship(
    #     "User", back_populates="Requirements"
    # )  # Relationship to the User class


class Libraries(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "libraries"  # Name of the table in the database
    __tableargs__ = {"comment": "Libraries that the user writes"}

    # Define the columns of the table
    library = Column(String(200), unique=False, index=True)  # library
    description = Column(String(5000), unique=False, index=True)  # description
    currentVersion = Column(String(50), unique=False, index=True)  # currentVersion
    newVersion = Column(String(50), unique=False, index=True)  # newVersion
    vulnerabilities = Column(JSON)  # vulnerabilities
    # Define the parent relationship to the User class
    # user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
    # user = relationship(
    #     "User", back_populates="Libraries"
    # )  # Relationship to the User clas

