# -*- coding: utf-8 -*-

import sqlalchemy  # Importing the sqlalchemy module
from com_lib.db_setup import (
    metadata,
)  # Importing the metadata module from the com_lib.db_setup package

# Defining a table named 'libraries' with various columns using the sqlalchemy library
libraries = sqlalchemy.Table(
    "libraries",  # Name of the table
    metadata,  # Metadata object to associate the table with
    sqlalchemy.Column(
        "id", sqlalchemy.String, primary_key=True
    ),  # Column named 'id' of type String and primary key constraint
    sqlalchemy.Column(
        "request_group_id", sqlalchemy.String, index=True
    ),  # Column named 'request_group_id' of type String and indexed
    sqlalchemy.Column(
        "library", sqlalchemy.String, index=True
    ),  # Column named 'library' of type String and indexed
    sqlalchemy.Column(
        "currentVersion", sqlalchemy.String, index=True
    ),  # Column named 'currentVersion' of type String and indexed
    sqlalchemy.Column(
        "newVersion", sqlalchemy.String, index=True
    ),  # Column named 'newVersion' of type String and indexed
    sqlalchemy.Column(
        "date_created", sqlalchemy.DateTime, index=True
    ),  # Column named 'date_created' of type DateTime and indexed
)

# Defining a table named 'requirements' with various columns using the sqlalchemy library
requirements = sqlalchemy.Table(
    "requirements",  # Name of the table
    metadata,  # Metadata object to associate the table with
    sqlalchemy.Column(
        "id", sqlalchemy.String, primary_key=True
    ),  # Column named 'id' of type String and primary key constraint
    sqlalchemy.Column(
        "request_group_id", sqlalchemy.String, unique=True, index=True
    ),  # Column named 'request_group_id' of type String with unique constraint and indexed
    sqlalchemy.Column(
        "text_in", sqlalchemy.String
    ),  # Column named 'text_in' of type String
    sqlalchemy.Column(
        "json_data_in", sqlalchemy.JSON
    ),  # Column named 'json_data_in' of type JSON
    sqlalchemy.Column(
        "json_data_out", sqlalchemy.JSON
    ),  # Column named 'json_data_out' of type JSON
    sqlalchemy.Column(
        "lib_out_count", sqlalchemy.Integer
    ),  # Column named 'lib_out_count' of type Integer
    sqlalchemy.Column(
        "host_ip", sqlalchemy.String, index=True
    ),  # Column named 'host_ip' of type String and indexed
    sqlalchemy.Column(
        "header_data", sqlalchemy.JSON
    ),  # Column named 'header_data' of type JSON
    sqlalchemy.Column(
        "date_created", sqlalchemy.DateTime, index=True
    ),  # Column named 'date_created' of type DateTime and indexed
)
