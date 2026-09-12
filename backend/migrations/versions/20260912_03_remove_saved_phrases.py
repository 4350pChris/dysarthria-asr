"""Remove saved phrases, categories, and grammar templates.

Revision ID: 20260912_03
Revises: 20260808_02
"""

import sqlalchemy as sa
from alembic import op

revision = "20260912_03"
down_revision = "20260808_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("phrases")
    op.drop_table("categories")
    op.drop_table("grammar_slot_values")
    op.drop_table("grammar_patterns")
    op.drop_table("grammar_slots")


def downgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
    )
    op.create_table(
        "phrases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.UniqueConstraint("category_id", "text"),
    )
    op.create_table(
        "grammar_slots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
    )
    op.create_table(
        "grammar_patterns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey("grammar_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.UniqueConstraint("slot_id", "template"),
    )
    op.create_table(
        "grammar_slot_values",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey("grammar_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.UniqueConstraint("slot_id", "value"),
    )
