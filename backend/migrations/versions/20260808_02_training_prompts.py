"""Store Tatoeba prompts in SQLite."""

import sqlalchemy as sa
from alembic import op

revision = "20260808_02"
down_revision = "20260808_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "training_prompts" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "training_prompts",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("split", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False, server_default="general"),
        sa.Column("source", sa.Text(), nullable=False, server_default="tatoeba"),
    )
    op.create_index("ix_training_prompts_split_id", "training_prompts", ["split", "id"])


def downgrade() -> None:
    raise RuntimeError("This migration protects local user data and cannot be downgraded.")
