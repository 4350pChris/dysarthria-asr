from enum import StrEnum
from typing import Optional

from sqlalchemy import CheckConstraint, Index
from sqlmodel import Field, Relationship, SQLModel


class AudioSource(StrEnum):
    APP_RECORDING = "app_recording"
    WHATSAPP_UPLOAD = "whatsapp_upload"
    TRAINING_READING = "training_reading"


class AsrSource(StrEnum):
    BROWSER = "browser"
    SERVER = "server"


class LabelStatus(StrEnum):
    DRAFT = "draft"
    LABELED = "labeled"
    SKIPPED = "skipped"


class Category(SQLModel, table=True):
    __tablename__ = "categories"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    phrases: list["Phrase"] = Relationship(
        back_populates="category",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class Phrase(SQLModel, table=True):
    __tablename__ = "phrases"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    category_id: int = Field(foreign_key="categories.id", ondelete="CASCADE")
    text: str
    category: Category | None = Relationship(back_populates="phrases")


class AudioClip(SQLModel, table=True):
    __tablename__ = "audio_clips"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (CheckConstraint("source IN ('app_recording', 'whatsapp_upload', 'training_reading')", name="audio_source"),)

    id: str = Field(primary_key=True)
    file_path: str
    original_filename: str = ""
    content_type: str = ""
    source: str
    created_at: str
    label: Optional["TranscriptionLabel"] = Relationship(
        back_populates="audio_clip",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False},
    )


class TranscriptionLabel(SQLModel, table=True):
    __tablename__ = "transcription_labels"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (CheckConstraint("asr_source IN ('browser', 'server')", name="asr_source"), CheckConstraint("status IN ('draft', 'labeled', 'skipped')", name="label_status"))

    id: int | None = Field(default=None, primary_key=True)
    audio_id: str = Field(foreign_key="audio_clips.id", ondelete="CASCADE", unique=True)
    asr_text: str = ""
    asr_source: str = AsrSource.SERVER.value
    transcript: str = ""
    status: str = LabelStatus.DRAFT.value
    unsure: bool = False
    notes: str = ""
    training_prompt_id: str = ""
    training_split: str = "train"
    training_category: str = ""
    training_prompt_source: str = ""
    updated_at: str
    audio_clip: AudioClip | None = Relationship(back_populates="label")


class TrainingPrompt(SQLModel, table=True):
    __tablename__ = "training_prompts"  # pyright: ignore[reportAssignmentType]
    __table_args__ = (Index("ix_training_prompts_split_id", "split", "id"),)

    id: str = Field(primary_key=True)
    text: str
    split: str
    category: str = "general"
    source: str = "tatoeba"


class GrammarSlot(SQLModel, table=True):
    __tablename__ = "grammar_slots"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    patterns: list["GrammarPattern"] = Relationship(back_populates="slot")
    values: list["GrammarSlotValue"] = Relationship(back_populates="slot")


class GrammarPattern(SQLModel, table=True):
    __tablename__ = "grammar_patterns"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    slot_id: int = Field(foreign_key="grammar_slots.id", ondelete="CASCADE")
    template: str
    slot: GrammarSlot | None = Relationship(back_populates="patterns")


class GrammarSlotValue(SQLModel, table=True):
    __tablename__ = "grammar_slot_values"  # pyright: ignore[reportAssignmentType]

    id: int | None = Field(default=None, primary_key=True)
    slot_id: int = Field(foreign_key="grammar_slots.id", ondelete="CASCADE")
    value: str
    slot: GrammarSlot | None = Relationship(back_populates="values")
