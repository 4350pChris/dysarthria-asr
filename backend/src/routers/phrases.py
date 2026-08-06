from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Form, status

from ..candidates import read_generated_candidates
from ..form_models import CategoryForm, CreatePhraseForm, GrammarPatternForm, GrammarValueForm, PhraseForm
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


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def add_category(data: Annotated[CategoryForm, Form()]) -> dict:
    return create_category(data.name)


@router.patch("/categories/{category_id}")
async def edit_category(category_id: int, data: Annotated[CategoryForm, Form()]) -> dict:
    return update_category(category_id, data.name)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_category(category_id: int) -> None:
    delete_category(category_id)


@router.post("/phrases", status_code=status.HTTP_201_CREATED)
async def add_phrase(data: Annotated[CreatePhraseForm, Form()]) -> dict:
    return create_phrase(data.category_id, data.text)


@router.patch("/phrases/{phrase_id}")
async def edit_phrase(phrase_id: int, data: Annotated[PhraseForm, Form()]) -> dict:
    return update_phrase(phrase_id, data.text)


@router.delete("/phrases/{phrase_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_phrase(phrase_id: int) -> None:
    delete_phrase(phrase_id)


@router.patch("/grammar/patterns/{pattern_id}")
async def edit_grammar_pattern(
    pattern_id: int,
    data: Annotated[GrammarPatternForm, Form()],
) -> dict:
    return update_grammar_pattern(pattern_id, data.template)


@router.patch("/grammar/values/{value_id}")
async def edit_grammar_value(
    value_id: int,
    data: Annotated[GrammarValueForm, Form()],
) -> dict:
    return update_grammar_value(value_id, data.value)
