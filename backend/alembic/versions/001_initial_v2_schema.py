"""Initial v2 schema with milestones and progress logs

Revision ID: 001
Revises:
Create Date: 2026-01-20

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "resolutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("goal_statement", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("skill_level", sa.String(length=50), nullable=True),
        sa.Column("cadence", sa.String(length=50), nullable=False),
        sa.Column("learning_sources", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("current_milestone", sa.Integer(), nullable=False),
        sa.Column("roadmap_generated", sa.Boolean(), nullable=False),
        sa.Column("roadmap_needs_refresh", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resolutions_id"), "resolutions", ["id"], unique=False)
    op.create_index(
        op.f("ix_resolutions_user_id"), "resolutions", ["user_id"], unique=False
    )

    op.create_table(
        "milestones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("verification_criteria", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("is_edited", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_milestones_id"), "milestones", ["id"], unique=False)
    op.create_index(
        op.f("ix_milestones_resolution_id"),
        "milestones",
        ["resolution_id"],
        unique=False,
    )

    op.create_table(
        "progress_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("input_type", sa.String(length=50), nullable=False),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("concepts_claimed", sa.JSON(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("verification_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_progress_logs_id"), "progress_logs", ["id"], unique=False)
    op.create_index(
        op.f("ix_progress_logs_resolution_id"),
        "progress_logs",
        ["resolution_id"],
        unique=False,
    )

    op.create_table(
        "verification_quizzes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("progress_log_id", sa.Integer(), nullable=False),
        sa.Column("questions", sa.JSON(), nullable=False),
        sa.Column("responses", sa.JSON(), nullable=False),
        sa.Column("quiz_type", sa.String(length=50), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["progress_log_id"],
            ["progress_logs.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_verification_quizzes_id"), "verification_quizzes", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_verification_quizzes_progress_log_id"),
        "verification_quizzes",
        ["progress_log_id"],
        unique=True,
    )

    op.create_table(
        "streaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False),
        sa.Column("longest_streak", sa.Integer(), nullable=False),
        sa.Column("total_verified_days", sa.Integer(), nullable=False),
        sa.Column("last_log_date", sa.Date(), nullable=True),
        sa.Column("last_verified_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_streaks_id"), "streaks", ["id"], unique=False)
    op.create_index(
        op.f("ix_streaks_resolution_id"), "streaks", ["resolution_id"], unique=True
    )

    op.create_table(
        "weekly_reflections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("week_number", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_weekly_reflections_id"), "weekly_reflections", ["id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_weekly_reflections_id"), table_name="weekly_reflections")
    op.drop_table("weekly_reflections")
    op.drop_index(op.f("ix_streaks_resolution_id"), table_name="streaks")
    op.drop_index(op.f("ix_streaks_id"), table_name="streaks")
    op.drop_table("streaks")
    op.drop_index(
        op.f("ix_verification_quizzes_progress_log_id"),
        table_name="verification_quizzes",
    )
    op.drop_index(op.f("ix_verification_quizzes_id"), table_name="verification_quizzes")
    op.drop_table("verification_quizzes")
    op.drop_index(op.f("ix_progress_logs_resolution_id"), table_name="progress_logs")
    op.drop_index(op.f("ix_progress_logs_id"), table_name="progress_logs")
    op.drop_table("progress_logs")
    op.drop_index(op.f("ix_milestones_resolution_id"), table_name="milestones")
    op.drop_index(op.f("ix_milestones_id"), table_name="milestones")
    op.drop_table("milestones")
    op.drop_index(op.f("ix_resolutions_user_id"), table_name="resolutions")
    op.drop_index(op.f("ix_resolutions_id"), table_name="resolutions")
    op.drop_table("resolutions")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
