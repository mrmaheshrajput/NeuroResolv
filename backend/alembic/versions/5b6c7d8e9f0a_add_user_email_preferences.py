"""Add user email preferences table

Revision ID: 5b6c7d8e9f0a
Revises: 94dff1cc9cdd
Create Date: 2026-02-04
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "5b6c7d8e9f0a"
down_revision = "94dff1cc9cdd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_email_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("email_opt_in", sa.Boolean(), nullable=False, default=False),
        sa.Column("timezone", sa.String(100), nullable=False, default="UTC"),
        sa.Column("preferred_hour", sa.Integer(), nullable=False, default=9),
        sa.Column("last_email_sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_email_type", sa.String(50), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, default=sa.func.now()
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_user_email_preferences_user_id",
        "user_email_preferences",
        ["user_id"],
        unique=True,
    )
    # Index for querying users by timezone and hour for scheduled emails
    op.create_index(
        "ix_user_email_preferences_schedule",
        "user_email_preferences",
        ["email_opt_in", "timezone", "preferred_hour"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_email_preferences_schedule", "user_email_preferences")
    op.drop_index("ix_user_email_preferences_user_id", "user_email_preferences")
    op.drop_table("user_email_preferences")
