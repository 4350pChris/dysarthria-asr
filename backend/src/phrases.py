from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from .database import connect_db

def read_phrases() -> list[dict]:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT phrases.id, categories.name AS category, phrases.text
            FROM phrases
            JOIN categories ON categories.id = phrases.category_id
            ORDER BY categories.name COLLATE NOCASE, phrases.id
            """
        ).fetchall()
    return [
        {
            "id": row["id"],
            "category": row["category"],
            "text": row["text"],
        }
        for row in rows
    ]


def read_categories() -> list[dict]:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT categories.id, categories.name, COUNT(phrases.id) AS phrase_count
            FROM categories
            LEFT JOIN phrases ON phrases.category_id = categories.id
            GROUP BY categories.id
            ORDER BY categories.name COLLATE NOCASE, categories.id
            """
        ).fetchall()
    return [dict(row) for row in rows]

def create_category(name: str) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Category name is required.")
    with connect_db() as db:
        try:
            cursor = db.execute(
                "INSERT INTO categories (name) VALUES (?)",
                (clean_name,),
            )
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Category already exists.") from error
        return {"id": cursor.lastrowid, "name": clean_name, "phrase_count": 0}


def create_phrase(category_id: int, text: str) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Phrase text is required.")
    with connect_db() as db:
        category = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found.")
        cursor = db.execute(
            "INSERT INTO phrases (category_id, text) VALUES (?, ?)",
            (category_id, clean_text),
        )
        return {"id": cursor.lastrowid, "category_id": category_id, "text": clean_text}


def update_phrase(phrase_id: int, text: str) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise HTTPException(status_code=400, detail="Phrase text is required.")
    with connect_db() as db:
        cursor = db.execute("UPDATE phrases SET text = ? WHERE id = ?", (clean_text, phrase_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Phrase not found.")
        return {"id": phrase_id, "text": clean_text}


def delete_phrase(phrase_id: int) -> dict:
    with connect_db() as db:
        cursor = db.execute("DELETE FROM phrases WHERE id = ?", (phrase_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Phrase not found.")
        return {"ok": True}


def read_grammar() -> list[dict]:
    with connect_db() as db:
        slots = db.execute("SELECT id, name FROM grammar_slots ORDER BY id").fetchall()
        patterns = db.execute(
            """
            SELECT id, slot_id, template
            FROM grammar_patterns
            ORDER BY id
            """
        ).fetchall()
        values = db.execute(
            """
            SELECT id, slot_id, value
            FROM grammar_slot_values
            ORDER BY id
            """
        ).fetchall()
    return [
        {
            "id": slot["id"],
            "name": slot["name"],
            "patterns": [
                {"id": row["id"], "template": row["template"]}
                for row in patterns
                if row["slot_id"] == slot["id"]
            ],
            "values": [
                {"id": row["id"], "value": row["value"]}
                for row in values
                if row["slot_id"] == slot["id"]
            ],
        }
        for slot in slots
    ]


def update_grammar_pattern(pattern_id: int, template: str) -> dict:
    clean_template = template.strip()
    if not clean_template:
        raise HTTPException(status_code=400, detail="Template is required.")
    with connect_db() as db:
        pattern = db.execute(
            """
            SELECT grammar_slots.name
            FROM grammar_patterns
            JOIN grammar_slots ON grammar_slots.id = grammar_patterns.slot_id
            WHERE grammar_patterns.id = ?
            """,
            (pattern_id,),
        ).fetchone()
        if not pattern:
            raise HTTPException(status_code=404, detail="Grammar pattern not found.")

        marker = "{" + pattern["name"] + "}"
        if clean_template.count(marker) != 1:
            raise HTTPException(status_code=400, detail="Template must contain the grammar slot once.")

        cursor = db.execute(
            "UPDATE grammar_patterns SET template = ? WHERE id = ?",
            (clean_template, pattern_id),
        )
    return {"id": pattern_id, "template": clean_template}


def update_grammar_value(value_id: int, value: str) -> dict:
    clean_value = value.strip()
    if not clean_value:
        raise HTTPException(status_code=400, detail="Value is required.")
    with connect_db() as db:
        cursor = db.execute(
            "UPDATE grammar_slot_values SET value = ? WHERE id = ?",
            (clean_value, value_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Grammar value not found.")
    return {"id": value_id, "value": clean_value}
