from sqlalchemy import Column, Delete, ForeignKey, Integer, Select, String, Update, Boolean
from sqlalchemy.orm import relationship
from dsg_lib import base_schema
from .resources import async_db


class User(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "users"  # Name of the table in the database

    # Define the columns of the table
    first_name = Column(String, unique=False, index=True)  # First name of the user
    last_name = Column(String, unique=False, index=True)  # Last name of the user
    user_name = Column(String, unique=True, index=True)  # Last name of the user
    email = Column(String, unique=False, index=True, nullable=True)  # Email of the user, must be unique
    password = Column(String, unique=False, index=True)  # Password of the user
    is_active = Column(Boolean, default=True)  # If the user is active
    is_admin = Column(Boolean, default=False)  # If the user is an admin

    # combine first and last name into a full name
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class InterestingThings(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "interesting_things"  # Name of the table in the database

    # Define the columns of the table
    name = Column(String, unique=False, index=True)  # name of item
    description = Column(String, unique=False, index=True)  # description of item
    url = Column(String, unique=False, index=True)  # url of item

#     # Define the parent relationship to the User class
#     user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
#     user = relationship(
#         "User", back_populates="InterestingThings"
#     )  # Relationship to the User class
#     category_id = Column(Integer, ForeignKey("categories.pkid"))  # Foreign key to the Categories table
#     categories = relationship(
#         "Categories", back_populates="InterestingThings"
#     )  # Relationship to the Categories class
    

class Categories(base_schema.SchemaBase, async_db.Base):
    __tablename__ = "categories"  # Name of the table in the database

    # Define the columns of the table
    name = Column(String, unique=False, index=True)  # name of item
    description = Column(String, unique=False, index=True)  # description of item
    is_system = Column(Boolean, default=True)  # If the category is a system default
    is_active = Column(Boolean, default=True)  # If the category is active
#     # Define the parent relationship to the User class
#     user_id = Column(Integer, ForeignKey("users.pkid"))  # Foreign key to the User table
#     user = relationship(
#         "User", back_populates="Categories"
#     )  # Relationship to the User class
#     # Define the parent relationship to the Categories class
#     category_id = Column(Integer, ForeignKey("categories.pkid"))  # Foreign key to the Categories table
#     Categories = relationship(
#         "Categories", back_populates="Categories"
#     )  # Relationship to the Categories class

