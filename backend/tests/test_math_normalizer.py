from __future__ import annotations

import pytest

from src.math_normalizer import normalize_german_math


@pytest.mark.parametrize(
    ("spoken", "math_text"),
    [
        ("zwei hoch vier.", "2^4"),
        ("wurzel von sechzehn.", "√16"),
        ("ein halb.", "1/2"),
        ("bruch drei durch vier.", "3/4"),
        ("zwei komma fünf.", "2,5"),
        ("fünf prozent.", "5%"),
        ("x ist gleich minus fünf.", "x = -5"),
        ("zwei pi.", "2 π"),
    ],
)
def test_normalizes_spoken_german_math(spoken: str, math_text: str) -> None:
    assert normalize_german_math(spoken).math_text == math_text
