from __future__ import annotations

import re
from functools import cache

from emoji import EMOJI_DATA
from emoji.unicode_codes import load_from_json

EMOJI_MARKERS = {"emoji", "emojis"}
WORD_PATTERN = re.compile(r"[\wäöüÄÖÜß]+", re.UNICODE)


@cache
def german_emoji_names() -> dict[tuple[str, ...], str]:
    """Return German CLDR short names, indexed by their spoken words."""
    names: dict[tuple[str, ...], str] = {}
    load_from_json("de")
    for value, data in EMOJI_DATA.items():
        shortcode = data.get("de")
        if not shortcode:
            continue
        name = shortcode.strip(":").replace("_", " ").casefold()
        words = tuple(WORD_PATTERN.findall(name))
        if words:
            names[words] = value
    return names


def replace_spoken_emojis(text: str) -> str:
    """Replace a German CLDR emoji name followed by the spoken marker "emoji"."""
    names = german_emoji_names()
    tokens = re.findall(r"[\wäöüÄÖÜß]+|\s+|[^\w\s]", text, re.UNICODE)

    for marker_index, token in enumerate(tokens):
        if token.casefold() not in EMOJI_MARKERS:
            continue

        word_positions = [
            index
            for index in range(marker_index)
            if WORD_PATTERN.fullmatch(tokens[index])
        ]
        for start_index in word_positions:
            words = tuple(
                token.casefold()
                for token in tokens[start_index:marker_index]
                if WORD_PATTERN.fullmatch(token)
            )
            if words not in names:
                continue
            tokens[start_index : marker_index + 1] = [names[words]]
            break

    return "".join(tokens)
