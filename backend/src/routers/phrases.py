from __future__ import annotations

from fastapi import APIRouter, Form

from ..candidates import read_generated_candidates
from ..phrases import (
    create_category,
    create_phrase,
    delete_phrase,
    read_grammar,
    read_categories,
    read_phrases,
    update_grammar_pattern,
    update_grammar_value,
    update_phrase,
)

router = APIRouter(prefix="/api")


@router.get("/phrases")
def list_phrases() -> list[dict]:
    return read_phrases()


@router.get("/categories")
def list_categories() -> list[dict]:
    return read_categories()


@router.get("/candidates/generated")
def list_generated_candidates() -> list[dict]:
    return read_generated_candidates()


@router.get("/grammar")
def list_grammar() -> list[dict]:
    return read_grammar()


@router.post("/categories")
async def add_category(name: str = Form(...)) -> dict:
    return create_category(name)


@router.post("/phrases")
async def add_phrase(category_id: int = Form(...), text: str = Form(...)) -> dict:
    return create_phrase(category_id, text)


@router.patch("/phrases/{phrase_id}")
async def edit_phrase(phrase_id: int, text: str = Form(...)) -> dict:
    return update_phrase(phrase_id, text)


@router.delete("/phrases/{phrase_id}")
def remove_phrase(phrase_id: int) -> dict:
    return delete_phrase(phrase_id)


@router.patch("/grammar/patterns/{pattern_id}")
async def edit_grammar_pattern(
    pattern_id: int,
    template: str = Form(...),
) -> dict:
    return update_grammar_pattern(pattern_id, template)


@router.patch("/grammar/values/{value_id}")
async def edit_grammar_value(
    value_id: int,
    value: str = Form(...),
) -> dict:
    return update_grammar_value(value_id, value)
