from __future__ import annotations

from fastapi import APIRouter, Form

from ..phrases import (
    create_category,
    create_phrase,
    delete_phrase,
    read_categories,
    read_phrases,
    update_phrase,
)

router = APIRouter(prefix="/api")


@router.get("/phrases")
def list_phrases() -> list[dict]:
    return read_phrases()


@router.get("/categories")
def list_categories() -> list[dict]:
    return read_categories()


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
