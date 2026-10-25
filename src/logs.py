# -*- coding: utf-8 -*-
"""Logging setup shared by both server entry points (main.py and rsgi.py)."""

import logging

from dsg_lib.common_functions import logging_config

from .settings import settings


def configure_logging() -> None:
    logging_config.config_log(
        logging_directory=settings.logging_directory,
        log_name=settings.log_name,
        logging_level=settings.logging_level,
        log_rotation=settings.log_rotation,
        log_retention=settings.log_retention,
        log_backtrace=settings.log_backtrace,
        log_serializer=settings.log_serializer,
        log_diagnose=settings.log_diagnose,
        intercept_standard_logging=settings.log_intercept_standard_logging,
    )
    # httpx logs every request at INFO - hundreds of lines for one large check.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
