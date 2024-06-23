"""
models.py

This module defines the data models used in the application.
It includes an enumeration for user roles.

Classes:
    RoleEnum: An enumeration representing different roles in the system.
"""

# -*- coding: utf-8 -*-

from enum import Enum


class RoleEnum(str, Enum):
    """
    Enum representing different roles in the system.

    Each role corresponds to a different set of permissions or capabilities within the system.

    Attributes:
        developer: Represents a developer role.
        interesting_things: Represents a role related to interesting things.
        job_applications: Represents a role related to job applications.
        notes: Represents a role related to notes.
        posts: Represents a role related to posts.
    """
    user_access="user_access"
    developer = "developer"  # Developer role
    interesting_things = "interesting_things"  # Role for handling interesting things
    job_applications = "job_applications"  # Role for handling job applications
    notes = "notes"  # Role for handling notes
    posts = "posts"  # Role for handling posts
