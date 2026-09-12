from __future__ import annotations

import bz2
import csv
import io
import json
import re
import tempfile
from pathlib import Path
from urllib.request import urlopen

TATOEBA_EXPORT_URL = "https://downloads.tatoeba.org/exports/per_language/deu/deu_sentences.tsv.bz2"
MIN_CHARACTERS = 25
MAX_CHARACTERS = 180
MAX_WORDS = 28
UNSAFE_PROMPT_PATTERN = re.compile(
    r"\b(?:anal(?:sex|verkehr)\w*|arsch(?:loch|geweih|kriecher)?|blasen|blowjob|cock|dick|ejakulat\w*|escort\w*|\w*fick\w*|fotze\w*|geschlechtsverkehr|hure\w*|kondom\w*|masturb\w*|muschi\w*|nackt\w*|nutte\w*|orgasmus\w*|penis\w*|porn\w*|prostitut\w*|pussy|rape\w*|schei[ßs]\w*|schlampe\w*|\w*sex\w*|sperma\w*|strip(?:club|per|pen)?\w*|vergewalt\w*|vagina\w*|vulva\w*|wichs\w*)\b",
    re.IGNORECASE,
)


def is_safe_prompt(text: str) -> bool:
    return UNSAFE_PROMPT_PATTERN.search(text) is None


def is_readable_prompt(text: str) -> bool:
    words = text.split()
    return (
        MIN_CHARACTERS <= len(text) <= MAX_CHARACTERS
        and len(words) <= MAX_WORDS
        and any(character.isalpha() for character in text)
        and "http" not in text.casefold()
        and "\n" not in text
        and is_safe_prompt(text)
    )


def parse_export(contents: bytes) -> list[dict[str, str]]:
    rows = csv.reader(
        io.TextIOWrapper(io.BytesIO(bz2.decompress(contents)), encoding="utf-8"),
        delimiter="\t",
    )
    prompts = []
    for row in rows:
        if len(row) < 3 or row[1] != "deu":
            continue
        text = row[2].strip()
        if is_readable_prompt(text):
            prompts.append({"id": row[0], "text": text})
    return prompts


def download_prompts(url: str = TATOEBA_EXPORT_URL) -> list[dict[str, str]]:
    with urlopen(url, timeout=30) as response:  # noqa: S310 -- fixed official export URL
        return parse_export(response.read())


def write_prompts(path: Path, prompts: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as temporary:
        json.dump(prompts, temporary, ensure_ascii=False)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def ensure_prompts(path: Path) -> None:
    if path.exists():
        prompts = json.loads(path.read_text(encoding="utf-8"))
        safe_prompts = [prompt for prompt in prompts if is_safe_prompt(prompt["text"])]
        if len(safe_prompts) != len(prompts):
            write_prompts(path, safe_prompts)
        return
    prompts = download_prompts()
    write_prompts(path, prompts)
