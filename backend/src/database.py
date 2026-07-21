from __future__ import annotations

import csv
import sqlite3

from .paths import DATA_DIR, DB_FILE, PHRASES_FILE, SEED_PHRASES_FILE

CATEGORY_TRANSLATIONS = {
    "greetings": "Begrüßung",
    "requests": "Wünsche",
    "care": "Pflege",
    "clarification": "Verständigung",
    "comfort": "Komfort",
    "objects": "Dinge",
    "locations": "Orte",
    "social": "Soziales",
    "daily": "Alltag",
}


def connect_db() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with connect_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS phrases (
                id INTEGER PRIMARY KEY,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                text TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS audio_samples (
                id TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL DEFAULT '',
                content_type TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS speech_attempts (
                id INTEGER PRIMARY KEY,
                audio_id TEXT NOT NULL REFERENCES audio_samples(id),
                source TEXT NOT NULL DEFAULT '',
                phrase_id INTEGER REFERENCES phrases(id),
                expected_text TEXT NOT NULL DEFAULT '',
                raw_transcript TEXT NOT NULL DEFAULT '',
                corrected_text TEXT NOT NULL,
                suggested_phrase_id INTEGER REFERENCES phrases(id),
                suggested_text TEXT NOT NULL DEFAULT '',
                suggestion_score REAL,
                was_understandable INTEGER NOT NULL DEFAULT 0,
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            )
            """
        )
        count = db.execute("SELECT COUNT(*) FROM phrases").fetchone()[0]
        for old, new in CATEGORY_TRANSLATIONS.items():
            db.execute("UPDATE OR IGNORE categories SET name = ? WHERE name = ?", (new, old))
        seed_file = PHRASES_FILE if PHRASES_FILE.exists() else SEED_PHRASES_FILE
        if count or not seed_file.exists():
            return
        with seed_file.open(newline="", encoding="utf-8") as f:
            for sort_order, row in enumerate(csv.DictReader(f), start=1):
                category = row["category"].strip()
                text = row["text"].strip()
                db.execute(
                    "INSERT OR IGNORE INTO categories (name, sort_order) VALUES (?, ?)",
                    (category, sort_order),
                )
                category_id = db.execute("SELECT id FROM categories WHERE name = ?", (category,)).fetchone()[0]
                db.execute(
                    "INSERT INTO phrases (category_id, text, sort_order) VALUES (?, ?, ?)",
                    (category_id, text, sort_order),
                )
