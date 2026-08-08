from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from .api_errors import field_error
from .database import commit
from .models import Category, GrammarPattern, GrammarSlot, GrammarSlotValue, Phrase


def read_phrases(session: Session) -> list[dict]:
    rows = session.exec(
        select(Phrase, Category).join(Category).order_by(col(Category.name), col(Phrase.id))
    ).all()
    return [{"id": phrase.id, "category": category.name, "text": phrase.text} for phrase, category in rows]


def read_categories(session: Session) -> list[dict]:
    categories = session.exec(select(Category).order_by(col(Category.name), col(Category.id))).all()
    return [{"id": category.id, "name": category.name, "phrase_count": len(category.phrases)} for category in categories]


def create_category(name: str, session: Session) -> dict:
    category = Category(name=name)
    try:
        session.add(category)
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "name", "category_exists") from error
    return {"id": category.id, "name": category.name, "phrase_count": 0}


def update_category(category_id: int, name: str, session: Session) -> dict:
    category = session.get(Category, category_id)
    if category is None:
        raise field_error(404, "name", "category_not_found")
    try:
        category.name = name
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "name", "category_exists") from error
    return {"id": category.id, "name": category.name}


def delete_category(category_id: int, session: Session) -> None:
    category = session.get(Category, category_id)
    if category is None:
        raise field_error(404, "category_id", "category_not_found")
    session.delete(category)
    commit(session)


def create_phrase(category_id: int, text: str, session: Session) -> dict:
    phrase = Phrase(category_id=category_id, text=text)
    if session.get(Category, category_id) is None:
        raise field_error(404, "category_id", "category_not_found")
    try:
        session.add(phrase)
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "text", "phrase_exists") from error
    return {"id": phrase.id, "category_id": phrase.category_id, "text": phrase.text}


def update_phrase(phrase_id: int, text: str, session: Session) -> dict:
    phrase = session.get(Phrase, phrase_id)
    if phrase is None:
        raise field_error(404, "text", "phrase_not_found")
    try:
        phrase.text = text
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "text", "phrase_exists") from error
    return {"id": phrase.id, "text": phrase.text}


def delete_phrase(phrase_id: int, session: Session) -> None:
    phrase = session.get(Phrase, phrase_id)
    if phrase is None:
        raise HTTPException(status_code=404, detail=[{"loc": ["path", "phrase_id"], "type": "phrase_not_found"}])
    session.delete(phrase)
    commit(session)


def read_grammar(session: Session) -> list[dict]:
    slots = session.exec(select(GrammarSlot).order_by(col(GrammarSlot.id))).all()
    return [{"id": slot.id, "name": slot.name, "patterns": [{"id": item.id, "template": item.template} for item in slot.patterns], "values": [{"id": item.id, "value": item.value} for item in slot.values]} for slot in slots]


def update_grammar_pattern(pattern_id: int, template: str, session: Session) -> dict:
    pattern = session.get(GrammarPattern, pattern_id)
    if pattern is None:
        raise field_error(404, "template", "grammar_pattern_not_found")
    if pattern.slot is None:
        raise field_error(500, "template", "grammar_slot_missing")
    if template.count("{" + pattern.slot.name + "}") != 1:
        raise field_error(422, "template", "grammar_placeholder_invalid")
    try:
        pattern.template = template
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "template", "grammar_pattern_exists") from error
    return {"id": pattern.id, "template": pattern.template}


def update_grammar_value(value_id: int, value: str, session: Session) -> dict:
    item = session.get(GrammarSlotValue, value_id)
    if item is None:
        raise field_error(404, "value", "grammar_value_not_found")
    try:
        item.value = value
        commit(session)
    except IntegrityError as error:
        raise field_error(409, "value", "grammar_value_exists") from error
    return {"id": item.id, "value": item.value}
