from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from .api_errors import field_error
from .models import Category, GrammarPattern, GrammarSlot, GrammarSlotValue, Phrase
from .database import commit


def read_phrases(session: Session) -> list[dict]:
    rows = session.exec(select(Phrase, Category).join(Category).order_by(Category.name, Phrase.id)).all()
    return [{"id": phrase.id, "category": category.name, "text": phrase.text} for phrase, category in rows]


def read_categories(session: Session) -> list[dict]:
    categories = session.exec(select(Category).order_by(Category.name, Category.id)).all()
    return [{"id": category.id, "name": category.name, "phrase_count": len(category.phrases)} for category in categories]


def create_category(name: str, session: Session) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise field_error(422, "name", "value_required")
    category = Category(name=clean_name)
    try:
        with session.begin():
            session.add(category)
    except IntegrityError as error:
        raise field_error(409, "name", "category_exists") from error
    return {"id": category.id, "name": category.name, "phrase_count": 0}


def update_category(category_id: int, name: str, session: Session) -> dict:
    clean_name = name.strip()
    if not clean_name:
        raise field_error(422, "name", "value_required")
    try:
        with session.begin():
            category = session.get(Category, category_id)
            if category is None:
                raise field_error(404, "name", "category_not_found")
            category.name = clean_name
    except IntegrityError as error:
        raise field_error(409, "name", "category_exists") from error
    return {"id": category.id, "name": category.name}


def delete_category(category_id: int, session: Session) -> None:
    with session.begin():
        category = session.get(Category, category_id)
        if category is None:
            raise field_error(404, "category_id", "category_not_found")
        session.delete(category)


def create_phrase(category_id: int, text: str, session: Session) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise field_error(422, "text", "value_required")
    phrase = Phrase(category_id=category_id, text=clean_text)
    try:
        with session.begin():
            if session.get(Category, category_id) is None:
                raise field_error(404, "category_id", "category_not_found")
            session.add(phrase)
    except IntegrityError as error:
        raise field_error(409, "text", "phrase_exists") from error
    return {"id": phrase.id, "category_id": phrase.category_id, "text": phrase.text}


def update_phrase(phrase_id: int, text: str, session: Session) -> dict:
    clean_text = text.strip()
    if not clean_text:
        raise field_error(422, "text", "value_required")
    try:
        with session.begin():
            phrase = session.get(Phrase, phrase_id)
            if phrase is None:
                raise field_error(404, "text", "phrase_not_found")
            phrase.text = clean_text
    except IntegrityError as error:
        raise field_error(409, "text", "phrase_exists") from error
    return {"id": phrase.id, "text": phrase.text}


def delete_phrase(phrase_id: int, session: Session) -> None:
    with session.begin():
        phrase = session.get(Phrase, phrase_id)
        if phrase is None:
            raise HTTPException(status_code=404, detail=[{"loc": ["path", "phrase_id"], "type": "phrase_not_found"}])
        session.delete(phrase)


def read_grammar(session: Session) -> list[dict]:
    slots = session.exec(select(GrammarSlot).order_by(GrammarSlot.id)).all()
    return [{"id": slot.id, "name": slot.name, "patterns": [{"id": item.id, "template": item.template} for item in slot.patterns], "values": [{"id": item.id, "value": item.value} for item in slot.values]} for slot in slots]


def update_grammar_pattern(pattern_id: int, template: str, session: Session) -> dict:
    clean_template = template.strip()
    if not clean_template:
        raise field_error(422, "template", "value_required")
    try:
        with session.begin():
            pattern = session.get(GrammarPattern, pattern_id)
            if pattern is None:
                raise field_error(404, "template", "grammar_pattern_not_found")
            if clean_template.count("{" + pattern.slot.name + "}") != 1:
                raise field_error(422, "template", "grammar_placeholder_invalid")
            pattern.template = clean_template
    except IntegrityError as error:
        raise field_error(409, "template", "grammar_pattern_exists") from error
    return {"id": pattern.id, "template": pattern.template}


def update_grammar_value(value_id: int, value: str, session: Session) -> dict:
    clean_value = value.strip()
    if not clean_value:
        raise field_error(422, "value", "value_required")
    try:
        with session.begin():
            item = session.get(GrammarSlotValue, value_id)
            if item is None:
                raise field_error(404, "value", "grammar_value_not_found")
            item.value = clean_value
    except IntegrityError as error:
        raise field_error(409, "value", "grammar_value_exists") from error
    return {"id": item.id, "value": item.value}
