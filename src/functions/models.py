# -*- coding: utf-8 -*-

from enum import Enum


class RoleEnum(str, Enum):
    developer = "developer"
    interesting_things = "interesting_things"
    job_applications = "job_applications"
    notes = "notes"
    posts = "posts"
