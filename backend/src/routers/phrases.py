from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from sqlmodel import Session

from ..candidates import read_generated_candidates
from ..database import get_session
from ..phrases import (
    create_category,
    create_phrase,
    delete_category,
    delete_phrase,
    read_grammar,
    read_categories,
    read_phrases,
    update_grammar_pattern,
    update_grammar_value,
    update_category,
    update_phrase,
)

router = APIRouter(prefix="/api")

RequiredText = Annotated[str, Body(embed=True, min_length=1)]


@router.get("/phrases")
def list_phrases(session: Session = Depends(get_session)) -> list[dict]:
    return read_phrases(session)


@router.get("/categories")
def list_categories(session: Session = Depends(get_session)) -> list[dict]:
    return read_categories(session)


@router.get("/candidates/generated")
def list_generated_candidates(session: Session = Depends(get_session)) -> list[dict]:
    return read_generated_candidates(session)


@router.get("/grammar")
def list_grammar(session: Session = Depends(get_session)) -> list[dict]:
    return read_grammar(session)


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def add_category(name: RequiredText, session: Session = Depends(get_session)) -> dict:
    return create_category(name, session)


@router.patch("/categories/{category_id}")
def edit_category(category_id: int, name: RequiredText, session: Session = Depends(get_session)) -> dict:
    return update_category(category_id, name, session)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(category_id: int, session: Session = Depends(get_session)) -> None:
    delete_category(category_id, session)


@router.post("/phrases", status_code=status.HTTP_201_CREATED)
def add_phrase(
    category_id: Annotated[int, Body(embed=True)],
    text: RequiredText,
    session: Session = Depends(get_session),
) -> dict:
    return create_phrase(category_id, text, session)


@router.patch("/phrases/{phrase_id}")
def edit_phrase(phrase_id: int, text: RequiredText, session: Session = Depends(get_session)) -> dict:
    return update_phrase(phrase_id, text, session)


@router.delete("/phrases/{phrase_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_phrase(phrase_id: int, session: Session = Depends(get_session)) -> None:
    delete_phrase(phrase_id, session)


@router.patch("/grammar/patterns/{pattern_id}")
def edit_grammar_pattern(
    pattern_id: int,
    template: RequiredText,
    session: Session = Depends(get_session),
) -> dict:
    return update_grammar_pattern(pattern_id, template, session)


@router.patch("/grammar/values/{value_id}")
def edit_grammar_value(
    value_id: int,
    value: RequiredText,
    session: Session = Depends(get_session),
) -> dict:
    return update_grammar_value(value_id, value, session)
