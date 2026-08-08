from __future__ import annotations

from difflib import SequenceMatcher

from sqlmodel import Session, select

from .models import GrammarPattern, GrammarSlot, GrammarSlotValue, Phrase
from .semantic_matching import semantic_scores
from .text import normalize_text

FUZZY_FALLBACK_THRESHOLD = 0.72


def read_generated_candidates(session: Session) -> list[dict]:
    rows = session.exec(select(GrammarPattern, GrammarSlot, GrammarSlotValue).join(GrammarSlot, GrammarPattern.slot_id == GrammarSlot.id).join(GrammarSlotValue, GrammarSlotValue.slot_id == GrammarSlot.id).order_by(GrammarPattern.id, GrammarSlotValue.id)).all()
    return [{"id": f"generated:{pattern.id}:{value.id}", "source": "generated", "text": pattern.template.replace("{" + slot.name + "}", value.value), "pattern_id": pattern.id, "slot_values": {slot.name: value.value}} for pattern, slot, value in rows]


def read_candidates(session: Session) -> list[dict]:
    phrases = session.exec(select(Phrase).order_by(Phrase.id)).all()
    candidates = [{"id": f"phrase:{phrase.id}", "source": "phrase", "text": phrase.text} for phrase in phrases] + read_generated_candidates(session)
    return list({normalize_text(item["text"]): item for item in reversed(candidates)}.values())


def candidate_suggestions(text: str, session: Session, limit: int = 5) -> list[dict]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    scored = [{**item, "score": round(SequenceMatcher(None, normalized, normalize_text(item["text"])).ratio(), 3)} for item in read_candidates(session)]
    best = max(scored, key=lambda item: item["score"], default={"score": 0})["score"]
    if best < FUZZY_FALLBACK_THRESHOLD:
        try:
            semantic_by_id = semantic_scores(text, scored)
            for item in scored:
                item["score"] = round(max(item["score"], semantic_by_id.get(item["id"], 0)), 3)
        except Exception:
            pass
    return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
