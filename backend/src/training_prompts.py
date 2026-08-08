from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .tatoeba import load_prompts, prompt_from_cache

def prompt_split(text: str) -> str:
    """Return a stable split without changing the cached Tatoeba source file."""
    split_key = " ".join(text.casefold().split())
    bucket = sha256(split_key.encode()).digest()[0] % 10
    if bucket < 8:
        return "train"
    if bucket == 8:
        return "validation"
    return "test"


def prompt_metadata(prompt: dict[str, str]) -> dict[str, str]:
    return {
        "id": f"tatoeba:{prompt['id']}",
        "text": prompt["text"],
        "category": "general",
        "source": "tatoeba",
        "split": prompt_split(prompt["text"]),
    }


def prompt_bank(path: Path) -> list[dict[str, str]]:
    return [prompt_metadata(prompt) for prompt in load_prompts(path)]


def find_prompt(path: Path, prompt_id: str) -> dict[str, str] | None:
    if not prompt_id.startswith("tatoeba:"):
        return None
    prompt = prompt_from_cache(path, prompt_id.removeprefix("tatoeba:"))
    return prompt_metadata(prompt) if prompt else None
