# -*- coding: utf-8 -*-
"""drop ocr_jobs table

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
Create Date: 2026-07-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "ocr_jobs" in existing:
        op.drop_table("ocr_jobs")


def downgrade() -> None:
    bind = op.get_bind()
    existing = set(inspect(bind).get_table_names())

    if "ocr_jobs" not in existing:
        op.create_table(
            "ocr_jobs",
            sa.Column("pkid", sa.String(36), primary_key=True),
            sa.Column("date_created", sa.DateTime(), nullable=True),
            sa.Column("date_updated", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=False, index=True),
            sa.Column("job_id", sa.String(), nullable=False, unique=True, index=True),
            sa.Column("original_filename", sa.String(), nullable=False),
            sa.Column("original_filepath", sa.String(), nullable=False),
            sa.Column("converted_filepath", sa.String(), nullable=True),
            sa.Column("status", sa.String(), nullable=True, index=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("file_size_original", sa.Integer(), nullable=True),
            sa.Column("file_size_converted", sa.Integer(), nullable=True),
            sa.Column("processing_duration", sa.Integer(), nullable=True),
            sa.Column("cleanup_after", sa.DateTime(), nullable=False, index=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.pkid"]),
        )
