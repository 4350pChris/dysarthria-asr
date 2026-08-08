from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from random import randrange

from sqlalchemy import func, insert, literal_column
from sqlmodel import Session, col, select

from .database import commit
from .models import TrainingPrompt

PROMPT_BATCH_SIZE = 1_000


def prompt_split(text: str) -> str:
    """Return a stable split without changing the cached Tatoeba source file."""
    split_key = " ".join(text.casefold().split())
    bucket = sha256(split_key.encode()).digest()[0] % 10
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def prompt_metadata(prompt: TrainingPrompt) -> dict[str, str]:
    return {
        "id": prompt.id,
        "text": prompt.text,
        "category": prompt.category,
        "source": prompt.source,
        "split": prompt.split,
    }


def import_prompts(path: Path, session: Session) -> int:
    if session.exec(select(TrainingPrompt.id).limit(1)).first() is not None:
        return 0
    prompts = json.loads(path.read_text(encoding="utf-8"))
    for offset in range(0, len(prompts), PROMPT_BATCH_SIZE):
        rows = [
            {
                "id": f"tatoeba:{prompt['id']}",
                "text": prompt["text"],
                "split": prompt_split(prompt["text"]),
                "category": "general",
                "source": "tatoeba",
            }
            for prompt in prompts[offset : offset + PROMPT_BATCH_SIZE]
        ]
        session.execute(insert(TrainingPrompt), rows)
    commit(session)
    return len(prompts)


def read_training_prompts(session: Session, limit: int = 200) -> list[dict[str, str]]:
    rowid = literal_column("rowid")
    maximum_rowid = session.exec(select(func.max(rowid)).select_from(TrainingPrompt)).one()
    if maximum_rowid is None:
        return []
    start_rowid = randrange(1, maximum_rowid + 1)
    prompts = list(session.exec(
        select(TrainingPrompt)
        .where(col(TrainingPrompt.split) == "train", rowid >= start_rowid)
        .limit(limit)
    ).all())
    if len(prompts) < limit:
        prompts += session.exec(
            select(TrainingPrompt)
            .where(col(TrainingPrompt.split) == "train", rowid < start_rowid)
            .limit(limit - len(prompts))
        ).all()
    return [prompt_metadata(prompt) for prompt in prompts]


def find_prompt(session: Session, prompt_id: str) -> dict[str, str] | None:
    prompt = session.get(TrainingPrompt, prompt_id)
    return prompt_metadata(prompt) if prompt else None
