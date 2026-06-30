"""add message feedback table

Revision ID: 20260630_0002
Revises: 20260629_0001
Create Date: 2026-06-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20260630_0002"
down_revision: str | None = "20260629_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "message_feedback",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("message_id", sa.String(length=36), nullable=False),
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("rating", sa.String(length=20), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "message_id",
            "user_id",
            name="uq_message_feedback_message_user",
        ),
    )
    op.create_index(
        op.f("ix_message_feedback_conversation_id"),
        "message_feedback",
        ["conversation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_feedback_message_id"),
        "message_feedback",
        ["message_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_message_feedback_user_id"),
        "message_feedback",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_message_feedback_user_id"),
        table_name="message_feedback",
    )
    op.drop_index(
        op.f("ix_message_feedback_message_id"),
        table_name="message_feedback",
    )
    op.drop_index(
        op.f("ix_message_feedback_conversation_id"),
        table_name="message_feedback",
    )
    op.drop_table("message_feedback")