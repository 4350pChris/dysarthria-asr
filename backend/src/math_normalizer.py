from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from text_to_num import alpha2digit

MATH_WORDS = [
    "null",
    "eins",
    "ein",
    "eine",
    "zwei",
    "drei",
    "vier",
    "fünf",
    "sechs",
    "sieben",
    "acht",
    "neun",
    "zehn",
    "elf",
    "zwölf",
    "dreizehn",
    "vierzehn",
    "fünfzehn",
    "sechzehn",
    "siebzehn",
    "achtzehn",
    "neunzehn",
    "zwanzig",
    "dreißig",
    "vierzig",
    "fünfzig",
    "sechzig",
    "siebzig",
    "achtzig",
    "neunzig",
    "hundert",
    "tausend",
    "und",
    "plus",
    "minus",
    "mal",
    "geteilt",
    "durch",
    "hoch",
    "quadrat",
    "wurzel",
    "aus",
    "von",
    "klammer",
    "auf",
    "zu",
    "größer",
    "kleiner",
    "gleich",
    "ist",
    "ergibt",
    "komma",
    "prozent",
    "halb",
    "drittel",
    "viertel",
    "fünftel",
    "sechstel",
    "siebtel",
    "achtel",
    "neuntel",
    "zehntel",
    "bruch",
    "pi",
    "x",
    "y",
    "a",
    "b",
]

NUMBER_WORDS = {
    "null": "0",
    "eins": "1",
    "ein": "1",
    "eine": "1",
    "zwei": "2",
    "drei": "3",
    "vier": "4",
    "fünf": "5",
    "sechs": "6",
    "sieben": "7",
    "acht": "8",
    "neun": "9",
    "zehn": "10",
    "elf": "11",
    "zwölf": "12",
}

REPLACEMENTS = [
    (r"\bist gleich\b", "="),
    (r"\bergibt\b", "="),
    (r"\bbruch ([\w.]+) durch ([\w.]+)\b", r"\1/\2"),
    (
        r"\b([\w.]+) (halb|drittel|viertel|fünftel|sechstel|siebtel|achtel|neuntel|zehntel)\b",
        lambda match: fraction(match.group(1), match.group(2)),
    ),
    (r"\b([\w.]+) komma ([\w.]+)\b", r"\1,\2"),
    (r"\b([\w.,]+) prozent\b", r"\1%"),
    (r"\bgeteilt durch\b", "/"),
    (r"\bgrößer gleich\b", "≥"),
    (r"\bkleiner gleich\b", "≤"),
    (r"\bgrößer als\b", ">"),
    (r"\bkleiner als\b", "<"),
    (r"\bgleich\b", "="),
    (r"\bplus\b", "+"),
    (r"\bminus\b", "-"),
    (r"\bmal\b", "*"),
    (r"\bpi\b", "π"),
    (r"\bklammer auf\b", "("),
    (r"\bklammer zu\b", ")"),
    (r"\bwurzel (aus|von) ([\w.]+)\b", r"√\2"),
    (r"\b(\w+) quadrat\b", r"\1²"),
    (r"\b(\w+) hoch (\w+)\b", r"\1^\2"),
]

DENOMINATORS = {
    "halb": "2",
    "drittel": "3",
    "viertel": "4",
    "fünftel": "5",
    "sechstel": "6",
    "siebtel": "7",
    "achtel": "8",
    "neuntel": "9",
    "zehntel": "10",
}


@dataclass
class MathNormalization:
    raw_text: str
    corrected_text: str
    number_text: str
    math_text: str


def normalize_for_match(text: str) -> str:
    return text.casefold().replace("ß", "ss").replace("ä", "a").replace("ö", "o").replace("ü", "u")


def fuzzy_math_word(word: str) -> str:
    normalized = normalize_for_match(word)
    if not normalized or normalized.isdigit() or len(normalized) <= 1:
        return word

    best = max(
        MATH_WORDS,
        key=lambda candidate: SequenceMatcher(None, normalized, normalize_for_match(candidate)).ratio(),
    )
    score = SequenceMatcher(None, normalized, normalize_for_match(best)).ratio()
    return best if score >= 0.7 else word


def correct_math_words(text: str) -> str:
    words = re.findall(r"[\wäöüÄÖÜß]+|[^\w\s]", text.casefold(), re.UNICODE)
    return " ".join(fuzzy_math_word(word) for word in words)


def compact_math_text(text: str) -> str:
    return (
        text.replace("( ", "(")
        .replace(" )", ")")
        .replace("√ ", "√")
        .replace(" ^ ", "^")
        .replace("- ", "-")
        .replace("²", "²")
        .rstrip(".!? ")
    )


def fraction(numerator: str, denominator_word: str) -> str:
    return f"{numerator}/{DENOMINATORS[denominator_word]}"


def replace_remaining_number_words(text: str) -> str:
    for word, number in NUMBER_WORDS.items():
        text = re.sub(rf"\b{word}\b", number, text)
    return text


def normalize_german_math(text: str) -> MathNormalization:
    corrected = correct_math_words(text)
    number_text = replace_remaining_number_words(alpha2digit(corrected, "de"))
    math_text = number_text
    for pattern, replacement in REPLACEMENTS:
        math_text = re.sub(pattern, replacement, math_text)

    return MathNormalization(
        raw_text=text,
        corrected_text=corrected,
        number_text=number_text,
        math_text=compact_math_text(math_text),
    )
