"""Add roadmap improvements schema

Revision ID: 4a2b3c4d5e6f
Revises: 323f38f90688
Create Date: 2026-01-31

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4a2b3c4d5e6f"
down_revision: Union[str, None] = "323f38f90688"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to resolutions table
    op.add_column(
        "resolutions",
        sa.Column(
            "roadmap_mode", sa.String(50), server_default="ai_generated", nullable=False
        ),
    )
    op.add_column(
        "resolutions", sa.Column("goal_likelihood_score", sa.Float(), nullable=True)
    )
    op.add_column(
        "resolutions", sa.Column("next_roadmap_refresh", sa.DateTime(), nullable=True)
    )

    # Create weekly_goals table
    op.create_table(
        "weekly_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("goal_text", sa.Text(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("week_end", sa.Date(), nullable=False),
        sa.Column("is_dismissed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_weekly_goals_id"), "weekly_goals", ["id"], unique=False)
    op.create_index(
        op.f("ix_weekly_goals_resolution_id"),
        "weekly_goals",
        ["resolution_id"],
        unique=False,
    )

    # Create north_star_goals table
    op.create_table(
        "north_star_goals",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("resolution_id", sa.Integer(), nullable=False),
        sa.Column("goal_statement", sa.Text(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=False),
        sa.Column(
            "is_ai_generated", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column("is_edited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["resolution_id"],
            ["resolutions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resolution_id"),
    )
    op.create_index(
        op.f("ix_north_star_goals_id"), "north_star_goals", ["id"], unique=False
    )
    op.create_index(
        op.f("ix_north_star_goals_resolution_id"),
        "north_star_goals",
        ["resolution_id"],
        unique=True,
    )

    # Create ai_feedback table
    op.create_table(
        "ai_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.String(20), nullable=False),
        sa.Column("feedback_text", sa.Text(), nullable=True),
        sa.Column(
            "was_regenerated", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column("regenerated_content_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_feedback_id"), "ai_feedback", ["id"], unique=False)
    op.create_index(
        op.f("ix_ai_feedback_user_id"), "ai_feedback", ["user_id"], unique=False
    )


def downgrade() -> None:
    # Drop tables
    op.drop_index(op.f("ix_ai_feedback_user_id"), table_name="ai_feedback")
    op.drop_index(op.f("ix_ai_feedback_id"), table_name="ai_feedback")
    op.drop_table("ai_feedback")

    op.drop_index(
        op.f("ix_north_star_goals_resolution_id"), table_name="north_star_goals"
    )
    op.drop_index(op.f("ix_north_star_goals_id"), table_name="north_star_goals")
    op.drop_table("north_star_goals")

    op.drop_index(op.f("ix_weekly_goals_resolution_id"), table_name="weekly_goals")
    op.drop_index(op.f("ix_weekly_goals_id"), table_name="weekly_goals")
    op.drop_table("weekly_goals")

    # Remove columns from resolutions
    op.drop_column("resolutions", "next_roadmap_refresh")
    op.drop_column("resolutions", "goal_likelihood_score")
    op.drop_column("resolutions", "roadmap_mode")
