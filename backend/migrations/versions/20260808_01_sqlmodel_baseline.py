"""Create the SQLModel schema and upgrade the legacy SQLite schema."""

import sqlalchemy as sa
from alembic import op

revision = "20260808_01"
down_revision = None
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table)}


def _audio_source_check_is_legacy() -> bool:
    checks = sa.inspect(op.get_bind()).get_check_constraints("audio_clips")
    return any("training_reading" not in (check.get("sqltext") or "") for check in checks)


def _label_checks_are_legacy() -> bool:
    checks = sa.inspect(op.get_bind()).get_check_constraints("transcription_labels")
    check_text = " ".join(check.get("sqltext") or "" for check in checks)
    return "asr_source IN ('browser', 'server')" not in check_text or "status IN ('draft', 'labeled', 'skipped')" not in check_text


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "categories" not in tables:
        op.create_table("categories", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.Text(), nullable=False, unique=True))
    if "phrases" not in tables:
        op.create_table("phrases", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("category_id", sa.Integer(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False), sa.Column("text", sa.Text(), nullable=False), sa.UniqueConstraint("category_id", "text"))
    if "audio_clips" not in tables:
        op.create_table("audio_clips", sa.Column("id", sa.Text(), primary_key=True), sa.Column("file_path", sa.Text(), nullable=False), sa.Column("original_filename", sa.Text(), nullable=False, server_default=""), sa.Column("content_type", sa.Text(), nullable=False, server_default=""), sa.Column("source", sa.Text(), nullable=False), sa.Column("created_at", sa.Text(), nullable=False), sa.CheckConstraint("source IN ('app_recording', 'whatsapp_upload', 'training_reading')", name="audio_source"))
    elif _audio_source_check_is_legacy():
        with op.batch_alter_table("audio_clips", recreate="always") as batch:
            batch.create_check_constraint("audio_source", "source IN ('app_recording', 'whatsapp_upload', 'training_reading')")
    if "transcription_labels" not in tables:
        op.create_table("transcription_labels", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("audio_id", sa.Text(), sa.ForeignKey("audio_clips.id", ondelete="CASCADE"), nullable=False, unique=True), sa.Column("asr_text", sa.Text(), nullable=False, server_default=""), sa.Column("asr_source", sa.Text(), nullable=False, server_default="server"), sa.Column("transcript", sa.Text(), nullable=False, server_default=""), sa.Column("status", sa.Text(), nullable=False, server_default="draft"), sa.Column("unsure", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("notes", sa.Text(), nullable=False, server_default=""), sa.Column("training_prompt_id", sa.Text(), nullable=False, server_default=""), sa.Column("training_split", sa.Text(), nullable=False, server_default="train"), sa.Column("training_category", sa.Text(), nullable=False, server_default=""), sa.Column("training_prompt_source", sa.Text(), nullable=False, server_default=""), sa.Column("updated_at", sa.Text(), nullable=False))
    elif "asr_source" not in _columns("transcription_labels"):
        op.add_column("transcription_labels", sa.Column("asr_source", sa.Text(), nullable=False, server_default="server"))
    if "transcription_labels" in tables and _label_checks_are_legacy():
        with op.batch_alter_table("transcription_labels", recreate="always") as batch:
            batch.create_check_constraint("asr_source", "asr_source IN ('browser', 'server')")
            batch.create_check_constraint("label_status", "status IN ('draft', 'labeled', 'skipped')")
    for column, default in (("training_prompt_id", ""), ("training_split", "train"), ("training_category", ""), ("training_prompt_source", "")):
        if "transcription_labels" in tables and column not in _columns("transcription_labels"):
            op.add_column("transcription_labels", sa.Column(column, sa.Text(), nullable=False, server_default=default))
    if "grammar_slots" not in tables:
        op.create_table("grammar_slots", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.Text(), nullable=False, unique=True))
        op.create_table("grammar_patterns", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slot_id", sa.Integer(), sa.ForeignKey("grammar_slots.id", ondelete="CASCADE"), nullable=False), sa.Column("template", sa.Text(), nullable=False), sa.UniqueConstraint("slot_id", "template"))
        op.create_table("grammar_slot_values", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("slot_id", sa.Integer(), sa.ForeignKey("grammar_slots.id", ondelete="CASCADE"), nullable=False), sa.Column("value", sa.Text(), nullable=False), sa.UniqueConstraint("slot_id", "value"))


def downgrade() -> None:
    raise RuntimeError("This migration protects local user data and cannot be downgraded.")
