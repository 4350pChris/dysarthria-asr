from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from secrets import randbelow

from sqlalchemy import delete, func, insert, literal_column
from sqlmodel import Session, col, select

from .database import commit
from .models import TrainingPrompt
from .tatoeba import is_safe_prompt

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
    prompts = json.loads(path.read_text(encoding="utf-8"))
    prompts = [prompt for prompt in prompts if is_safe_prompt(prompt["text"])]
    existing = session.exec(
        select(func.count()).select_from(TrainingPrompt).where(col(TrainingPrompt.source) == "tatoeba")
    ).one()
    if existing == len(prompts):
        return 0
    session.execute(delete(TrainingPrompt).where(col(TrainingPrompt.source) == "tatoeba"))
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
    maximum_train_rowid = session.exec(
        select(rowid)
        .where(col(TrainingPrompt.split) == "train")
        .order_by(rowid.desc())
        .limit(1)
    ).first()
    if maximum_train_rowid is None:
        return []
    start_rowid = randbelow(maximum_train_rowid) + 1
    prompts = list(session.exec(
        select(TrainingPrompt)
        .where(col(TrainingPrompt.split) == "train", rowid >= start_rowid)
        .order_by(rowid)
        .limit(limit)
    ).all())
    if len(prompts) < limit:
        prompts += session.exec(
            select(TrainingPrompt)
            .where(col(TrainingPrompt.split) == "train", rowid < start_rowid)
            .order_by(rowid)
            .limit(limit - len(prompts))
        ).all()
    return [prompt_metadata(prompt) for prompt in prompts if is_safe_prompt(prompt.text)]


def find_prompt(session: Session, prompt_id: str) -> dict[str, str] | None:
    prompt = session.get(TrainingPrompt, prompt_id)
    return prompt_metadata(prompt) if prompt and is_safe_prompt(prompt.text) else None
