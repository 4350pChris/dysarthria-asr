from __future__ import annotations

from difflib import SequenceMatcher

from .database import connect_db
from .semantic_matching import semantic_scores
from .text import normalize_text

FUZZY_FALLBACK_THRESHOLD = 0.72


def read_generated_candidates() -> list[dict]:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT
                grammar_patterns.id AS pattern_id,
                grammar_patterns.template,
                grammar_slots.name AS slot_name,
                grammar_slot_values.id AS value_id,
                grammar_slot_values.value
            FROM grammar_patterns
            JOIN grammar_slots ON grammar_slots.id = grammar_patterns.slot_id
            JOIN grammar_slot_values ON grammar_slot_values.slot_id = grammar_slots.id
            ORDER BY grammar_patterns.id, grammar_slot_values.id
            """
        ).fetchall()
    return [
        {
            "id": f"generated:{row['pattern_id']}:{row['value_id']}",
            "source": "generated",
            "text": row["template"].replace("{" + row["slot_name"] + "}", row["value"]),
            "pattern_id": row["pattern_id"],
            "slot_values": {row["slot_name"]: row["value"]},
        }
        for row in rows
    ]


def read_candidates() -> list[dict]:
    with connect_db() as db:
        rows = db.execute(
            """
            SELECT phrases.id, phrases.text
            FROM phrases
            ORDER BY phrases.id
            """
        ).fetchall()
    phrase_candidates = [
        {
            "id": f"phrase:{row['id']}",
            "source": "phrase",
            "text": row["text"],
        }
        for row in rows
    ]
    candidates = phrase_candidates + read_generated_candidates()
    return list({normalize_text(candidate["text"]): candidate for candidate in reversed(candidates)}.values())


def candidate_suggestions(text: str, limit: int = 5) -> list[dict]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    candidates = read_candidates()
    scored = []
    for candidate in candidates:
        score = SequenceMatcher(None, normalized, normalize_text(candidate["text"])).ratio()
        scored.append({**candidate, "score": round(score, 3)})

    best_fuzzy_item = max(scored, key=lambda item: item["score"], default=None)
    best_fuzzy = best_fuzzy_item["score"] if best_fuzzy_item else 0
    if best_fuzzy < FUZZY_FALLBACK_THRESHOLD:
        scored = apply_semantic_fallback(text, scored)

    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]


def apply_semantic_fallback(text: str, scored: list[dict]) -> list[dict]:
    try:
        semantic_by_id = semantic_scores(text, scored)
    except Exception:
        return scored

    for item in scored:
        semantic_score = semantic_by_id.get(item["id"], 0)
        item["score"] = round(max(item["score"], semantic_score), 3)
    return scored
