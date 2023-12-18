import openai
from dsg_lib import base_schema
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON
from sqlalchemy.orm import relationship

from .resources import async_db


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Call OpenAI to get tags
        openai.api_key = "your-api-key"
        response = openai.Completion.create(
            engine="text-davinci-002",
            prompt=f"Please analyze the following text and provide 1 to 3 one-word psychological keyword tags that best capture its essence: {self.note}",
            temperature=0.5,
            max_tokens=3,
        )

        # Store the tags as a JSON object
        self.tags = response.choices[0].text.strip().split()
