from __future__ import annotations

import sqlite3

from fastapi import HTTPException

from .api_errors import field_error
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
        raise field_error(422, "name", "value_required")
    with connect_db() as db:
        try:
            cursor = db.execute(
                "INSERT INTO categories (name) VALUES (?)",
                (clean_name,),
            )
        except sqlite3.IntegrityError as error:
            raise field_error(409, "name", "category_exists") from error
        return {"id": cursor.lastrowid, "name": clean_name, "phrase_count": 0}


def update_category(category_id: int, name: str) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise field_error(422, "name", "value_required")
    with connect_db() as db:
        try:
            cursor = db.execute("UPDATE categories SET name = ? WHERE id = ?", (clean_name, category_id))
        except sqlite3.IntegrityError as error:
            raise field_error(409, "name", "category_exists") from error
        if cursor.rowcount == 0:
            raise field_error(404, "name", "category_not_found")
    return {"id": category_id, "name": clean_name}


def delete_category(category_id: int) -> None:
    with connect_db() as db:
        category = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            raise field_error(404, "category_id", "category_not_found")
        db.execute("DELETE FROM phrases WHERE category_id = ?", (category_id,))
        db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
def create_phrase(category_id: int, text: str) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise field_error(422, "text", "value_required")
    with connect_db() as db:
        category = db.execute("SELECT id FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not category:
            raise field_error(404, "category_id", "category_not_found")
        try:
            cursor = db.execute(
                "INSERT INTO phrases (category_id, text) VALUES (?, ?)",
                (category_id, clean_text),
            )
        except sqlite3.IntegrityError as error:
            raise field_error(409, "text", "phrase_exists") from error
        return {"id": cursor.lastrowid, "category_id": category_id, "text": clean_text}


def update_phrase(phrase_id: int, text: str) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise field_error(422, "text", "value_required")
    with connect_db() as db:
        try:
            cursor = db.execute("UPDATE phrases SET text = ? WHERE id = ?", (clean_text, phrase_id))
        except sqlite3.IntegrityError as error:
            raise field_error(409, "text", "phrase_exists") from error
        if cursor.rowcount == 0:
            raise field_error(404, "text", "phrase_not_found")
        return {"id": phrase_id, "text": clean_text}


def delete_phrase(phrase_id: int) -> None:
    with connect_db() as db:
        cursor = db.execute("DELETE FROM phrases WHERE id = ?", (phrase_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=[{"loc": ["path", "phrase_id"], "type": "phrase_not_found"}])
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
        raise field_error(422, "template", "value_required")
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
            raise field_error(404, "template", "grammar_pattern_not_found")

        marker = "{" + pattern["name"] + "}"
        if clean_template.count(marker) != 1:
            raise field_error(422, "template", "grammar_placeholder_invalid")

        try:
            db.execute(
                "UPDATE grammar_patterns SET template = ? WHERE id = ?",
                (clean_template, pattern_id),
            )
        except sqlite3.IntegrityError as error:
            raise field_error(409, "template", "grammar_pattern_exists") from error
    return {"id": pattern_id, "template": clean_template}


def update_grammar_value(value_id: int, value: str) -> dict:
    clean_value = value.strip()
    if not clean_value:
        raise field_error(422, "value", "value_required")
    with connect_db() as db:
        try:
            cursor = db.execute(
                "UPDATE grammar_slot_values SET value = ? WHERE id = ?",
                (clean_value, value_id),
            )
        except sqlite3.IntegrityError as error:
            raise field_error(409, "value", "grammar_value_exists") from error
        if cursor.rowcount == 0:
            raise field_error(404, "value", "grammar_value_not_found")
    return {"id": value_id, "value": clean_value}
