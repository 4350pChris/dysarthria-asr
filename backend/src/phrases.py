from __future__ import annotations

import sqlite3
from difflib import SequenceMatcher

from fastapi import HTTPException

from .database import connect_db
from .semantic_matching import semantic_scores
from .text import normalize_text

FUZZY_FALLBACK_THRESHOLD = 0.72
SEMANTIC_WEIGHT = 0.65


def read_phrases() -> list[dict]:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT phrases.id, categories.name AS category, phrases.text
            FROM phrases
            JOIN categories ON categories.id = phrases.category_id
            WHERE phrases.active = 1
            ORDER BY categories.name COLLATE NOCASE, phrases.sort_order, phrases.id
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
            LEFT JOIN phrases ON phrases.category_id = categories.id AND phrases.active = 1
            GROUP BY categories.id
            ORDER BY categories.name COLLATE NOCASE, categories.id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def phrase_suggestions(text: str, limit: int = 3) -> list[dict]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    phrases = read_phrases()
    scored = []
    for phrase in phrases:
        score = SequenceMatcher(None, normalized, normalize_text(phrase.get("text", ""))).ratio()
        scored.append(
            {
                "phrase_id": phrase["id"],
                "text": phrase.get("text", ""),
                "score": round(score, 3),
            }
        )

    best_fuzzy = max((item["score"] for item in scored), default=0)
    if best_fuzzy < FUZZY_FALLBACK_THRESHOLD:
        scored = apply_semantic_fallback(text, phrases, scored)

    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def apply_semantic_fallback(text: str, phrases: list[dict], scored: list[dict]) -> list[dict]:
    try:
        semantic_by_id = semantic_scores(text, phrases)
    except Exception:
        return scored

    for item in scored:
        semantic_score = semantic_by_id.get(item["phrase_id"], 0)
        item["score"] = round(max(item["score"], semantic_score * SEMANTIC_WEIGHT), 3)
    return scored


def create_category(name: str) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Category name is required.")
    with connect_db() as db:
        sort_order = db.execute("SELECT COALESCE(MAX(sort_order), 0) + 1 FROM categories").fetchone()[0]
        try:
            cursor = db.execute(
                "INSERT INTO categories (name, sort_order) VALUES (?, ?)",
                (clean_name, sort_order),
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
        sort_order = db.execute(
            "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM phrases WHERE category_id = ?",
            (category_id,),
        ).fetchone()[0]
        cursor = db.execute(
            "INSERT INTO phrases (category_id, text, sort_order) VALUES (?, ?, ?)",
            (category_id, clean_text, sort_order),
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
        cursor = db.execute("UPDATE phrases SET active = 0 WHERE id = ?", (phrase_id,))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Phrase not found.")
        return {"ok": True}
