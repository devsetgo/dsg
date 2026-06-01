# -*- coding: utf-8 -*-
"""add notifications and ocr_jobs tables

Revision ID: a1b2c3d4e5f6
Revises: 7154ca3bffb4
Create Date: 2026-06-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "7154ca3bffb4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    if not bind.dialect.has_table(bind, "ocr_jobs"):
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

    if not bind.dialect.has_table(bind, "notifications"):
        op.create_table(
            "notifications",
            sa.Column("pkid", sa.String(36), primary_key=True),
            sa.Column("date_created", sa.DateTime(), nullable=True),
            sa.Column("date_updated", sa.DateTime(), nullable=True),
            sa.Column("user_id", sa.String(), nullable=False, index=True),
            sa.Column("message", sa.String(500), nullable=False),
            sa.Column("category", sa.String(50), nullable=True, index=True),
            sa.Column("is_read", sa.Boolean(), nullable=True, index=True),
            sa.Column("note_id", sa.String(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.pkid"]),
        )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("ocr_jobs")
